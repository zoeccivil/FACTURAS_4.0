"""
Gestor independiente de pagos de impuestos.
Módulo para gestionar pagos, reportes y exportación de impuestos sin integración con ITBIS adelantados.
"""

from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


class TaxPaymentManager:
    """
    Gestor centralizado para pagos de impuestos independiente del flujo contable.
    Funciones para marcar pagos, generar reportes mensuales y exportar a PDF.
    """

    @staticmethod
    def group_calculations_by_month(calculations: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Agrupa cálculos de impuestos por mes.
        
        Args:
            calculations: Lista de diccionarios con cálculos
            
        Returns:
            Diccionario keyed por "YYYY-MM" con listas de cálculos
        """
        grouped = defaultdict(list)
        
        for calc in calculations:
            try:
                # Intentar obtener fecha de creación en varios formatos
                date_raw = calc.get("creation_date") or calc.get("created_at") or ""
                
                if isinstance(date_raw, datetime):
                    date_obj = date_raw
                else:
                    # Parsear string de fecha
                    date_str = str(date_raw)[:10]  # "YYYY-MM-DD"
                    if date_str:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    else:
                        continue
                
                month_key = date_obj.strftime("%Y-%m")
                grouped[month_key].append(calc)
            except Exception:
                # Si hay error en fecha, agrupar en "Sin Fecha"
                grouped["Sin Fecha"].append(calc)
        
        return dict(sorted(grouped.items(), reverse=True))

    @staticmethod
    def calculate_payment_summary(calculations: List[Dict]) -> Dict:
        """
        Calcula resumen de pagos: totales, pagados, pendientes.
        
        Args:
            calculations: Lista de cálculos de impuestos
            
        Returns:
            Diccionario con totales, pagados, pendientes y porcentaje
        """
        total_amount = 0.0
        paid_amount = 0.0
        pending_amount = 0.0
        paid_count = 0
        pending_count = 0
        
        for calc in calculations:
            try:
                # Obtener monto del cálculo
                amount = float(calc.get("total_amount") or calc.get("amount") or 0)
                is_paid = bool(calc.get("is_paid", False))
                
                total_amount += amount
                
                if is_paid:
                    paid_amount += amount
                    paid_count += 1
                else:
                    pending_amount += amount
                    pending_count += 1
            except (ValueError, TypeError):
                continue
        
        paid_percentage = (paid_amount / total_amount * 100) if total_amount > 0 else 0
        
        return {
            "total_amount": total_amount,
            "paid_amount": paid_amount,
            "pending_amount": pending_amount,
            "paid_count": paid_count,
            "pending_count": pending_count,
            "paid_percentage": round(paid_percentage, 2),
            "total_count": paid_count + pending_count,
        }

    @staticmethod
    def calculate_monthly_summary(calculations_by_month: Dict[str, List[Dict]]) -> Dict[str, Dict]:
        """
        Calcula resumen de pagos para cada mes.
        
        Args:
            calculations_by_month: Diccionario agrupado por mes
            
        Returns:
            Diccionario con resumen por mes
        """
        monthly_summary = {}
        
        for month_key, calcs in calculations_by_month.items():
            summary = TaxPaymentManager.calculate_payment_summary(calcs)
            monthly_summary[month_key] = {
                **summary,
                "calculation_count": len(calcs),
            }
        
        return monthly_summary

    @staticmethod
    def format_currency(value: float, currency: str = "RD$") -> str:
        """Formatea un valor como moneda."""
        return f"{currency} {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def get_payment_status_text(is_paid: bool) -> str:
        """Retorna el texto de estado de pago."""
        return "✓ Pagado" if is_paid else "⧗ Pendiente"

    @staticmethod
    def generate_monthly_report_data(
        calculations: List[Dict],
        company_name: str = "",
        include_details: bool = True
    ) -> Dict:
        """
        Genera datos completos para reporte mensual.
        
        Args:
            calculations: Lista de cálculos de impuestos
            company_name: Nombre de la empresa
            include_details: Si incluir detalles de cada cálculo
            
        Returns:
            Diccionario con todos los datos para reporte
        """
        grouped = TaxPaymentManager.group_calculations_by_month(calculations)
        monthly_summary = TaxPaymentManager.calculate_monthly_summary(grouped)
        overall_summary = TaxPaymentManager.calculate_payment_summary(calculations)
        
        report_data = {
            "generated_at": datetime.now(),
            "company_name": company_name,
            "overall_summary": overall_summary,
            "monthly_data": {},
        }
        
        for month_key in sorted(grouped.keys(), reverse=True):
            calcs = grouped[month_key]
            summary = monthly_summary[month_key]
            
            month_entry = {
                "month": month_key,
                "summary": summary,
                "calculations": [],
            }
            
            if include_details:
                for calc in calcs:
                    month_entry["calculations"].append({
                        "name": calc.get("name") or calc.get("title") or "Sin Nombre",
                        "created_at": calc.get("creation_date") or calc.get("created_at") or "",
                        "amount": float(calc.get("total_amount") or calc.get("amount") or 0),
                        "is_paid": bool(calc.get("is_paid", False)),
                        "status": TaxPaymentManager.get_payment_status_text(
                            bool(calc.get("is_paid", False))
                        ),
                        "percent": calc.get("percent_to_pay") or calc.get("percent") or "N/A",
                    })
            
            report_data["monthly_data"][month_key] = month_entry
        
        return report_data

    @staticmethod
    def get_pending_calculations(calculations: List[Dict]) -> List[Dict]:
        """Retorna solo los cálculos pendientes de pago."""
        return [c for c in calculations if not bool(c.get("is_paid", False))]

    @staticmethod
    def get_paid_calculations(calculations: List[Dict]) -> List[Dict]:
        """Retorna solo los cálculos ya pagados."""
        return [c for c in calculations if bool(c.get("is_paid", False))]

    @staticmethod
    def calculate_total_to_collect(
        calculations: List[Dict],
        exclude_paid: bool = False
    ) -> float:
        """
        Calcula el total a cobrar a clientes.
        
        Args:
            calculations: Lista de cálculos
            exclude_paid: Si excluir cálculos ya pagados
            
        Returns:
            Monto total a cobrar
        """
        calcs = (
            TaxPaymentManager.get_pending_calculations(calculations)
            if exclude_paid
            else calculations
        )
        
        total = 0.0
        for calc in calcs:
            try:
                total += float(calc.get("total_amount") or calc.get("amount") or 0)
            except (ValueError, TypeError):
                continue
        
        return total
