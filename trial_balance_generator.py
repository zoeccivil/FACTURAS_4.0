"""
trial_balance_generator.py
-------------------------
Generador de Asientos de Prueba y Balanza de Comprobación. 

Funciones principales:
1. Leer facturas de ingresos/gastos
2. Leer gastos adicionales acumulativos
3. Generar asientos contables automáticos
4. Calcular balanza de comprobación
"""

import datetime
from typing import List, Dict, Any, Optional


class TrialBalanceGenerator: 
    """Generador de asientos de prueba desde facturas y gastos adicionales."""

    def __init__(self, controller):
        self.controller = controller
        self._db = controller._db if hasattr(controller, "_db") else None

    def generate_trial_entries(
        self,
        company_id,
        year:  int,
        month: int,
        auto_post: bool = False
    ) -> tuple[bool, str, List[Dict[str, Any]]]:
        """
        Genera asientos de prueba para un periodo. 

        Returns:
            (success, message, entries_list)
        """
        if not self._db:
            return False, "Base de datos no inicializada.", []

        try:
            entries = []

            # 1️⃣ GENERAR ASIENTOS DE FACTURAS DE INGRESO
            income_entries = self._generate_income_entries(company_id, year, month)
            entries.extend(income_entries)

            # 2️⃣ GENERAR ASIENTOS DE FACTURAS DE GASTO
            expense_entries = self._generate_expense_entries(company_id, year, month)
            entries.extend(expense_entries)

            # 3️⃣ GENERAR ASIENTOS DE GASTOS ADICIONALES ACUMULATIVOS
            additional_entries = self._generate_additional_expense_entries(
                company_id, year, month
            )
            entries.extend(additional_entries)

            # 4️⃣ SI AUTO_POST, GUARDAR EN FIRESTORE
            if auto_post: 
                for entry in entries:
                    ok, msg = self. controller.create_journal_entry(
                        company_id=company_id,
                        entry_date=entry["entry_date"],
                        reference=entry["reference"],
                        description=entry["description"],
                        lines=entry["lines"]
                    )
                    if not ok:
                        return False, f"Error guardando asiento: {msg}", entries

            return True, f"{len(entries)} asientos generados correctamente.", entries

        except Exception as e:
            print(f"[TRIAL_BALANCE] Error:  {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error generando asientos: {e}", []

    def _generate_income_entries(
        self,
        company_id,
        year: int,
        month: int
    ) -> List[Dict[str, Any]]: 
        """Genera asientos de facturas de ingreso."""
        entries = []

        try:
            # Obtener facturas de ingreso del mes
            month_str = f"{month:02d}"
            invoices = self. controller._query_invoices(
                company_id=company_id,
                month_str=month_str,
                year_int=year,
                tx_type="emitida"
            )

            for inv in invoices:
                invoice_number = inv. get("invoice_number", "")
                invoice_date = inv.get("invoice_date")
                third_party = inv.get("third_party_name", "Cliente")
                
                # Normalizar fecha
                if isinstance(invoice_date, str):
                    invoice_date = datetime.datetime.strptime(invoice_date[: 10], "%Y-%m-%d").date()
                elif hasattr(invoice_date, "date") and callable(invoice_date.date):
                    invoice_date = invoice_date.date()

                # Calcular valores
                total_rd = float(inv.get("total_amount_rd", 0.0) or 0.0)
                itbis = float(inv.get("itbis", 0.0) or 0.0)
                exchange_rate = float(inv.get("exchange_rate", 1.0) or 1.0)
                itbis_rd = itbis * exchange_rate
                base = total_rd - itbis_rd

                # Asiento: 
                # DÉBITO: Clientes Nacionales (1. 1.2.001)
                # CRÉDITO: Ventas de Servicios (4.1.1.001)
                # CRÉDITO:  ITBIS por Pagar (2.1.2.001)

                lines = [
                    {
                        "account_id": "1.1.2.001",
                        "account_name": "Clientes Nacionales",
                        "debit": total_rd,
                        "credit": 0.0,
                        "description":  f"Venta a {third_party}"
                    },
                    {
                        "account_id":  "4.1.1.001",
                        "account_name": "Ventas de Servicios",
                        "debit": 0.0,
                        "credit": base,
                        "description": f"Base imponible NCF {invoice_number}"
                    },
                    {
                        "account_id": "2.1.2.001",
                        "account_name": "ITBIS por Pagar",
                        "debit": 0.0,
                        "credit": itbis_rd,
                        "description": f"ITBIS NCF {invoice_number}"
                    }
                ]

                entries.append({
                    "entry_date": invoice_date,
                    "reference": f"NCF-{invoice_number}",
                    "description":  f"Factura de Ingreso - {third_party}",
                    "lines": lines
                })

        except Exception as e:
            print(f"[TRIAL_BALANCE] Error en ingresos: {e}")

        return entries

    def _generate_expense_entries(
        self,
        company_id,
        year: int,
        month: int
    ) -> List[Dict[str, Any]]: 
        """Genera asientos de facturas de gasto."""
        entries = []

        try:
            month_str = f"{month:02d}"
            invoices = self.controller._query_invoices(
                company_id=company_id,
                month_str=month_str,
                year_int=year,
                tx_type="gasto"
            )

            for inv in invoices:
                invoice_number = inv.get("invoice_number", "")
                invoice_date = inv.get("invoice_date")
                third_party = inv.get("third_party_name", "Proveedor")

                # Normalizar fecha
                if isinstance(invoice_date, str):
                    invoice_date = datetime.datetime.strptime(invoice_date[:10], "%Y-%m-%d").date()
                elif hasattr(invoice_date, "date") and callable(invoice_date.date):
                    invoice_date = invoice_date. date()

                total_rd = float(inv.get("total_amount_rd", 0.0) or 0.0)
                itbis = float(inv.get("itbis", 0.0) or 0.0)
                exchange_rate = float(inv.get("exchange_rate", 1.0) or 1.0)
                itbis_rd = itbis * exchange_rate
                base = total_rd - itbis_rd

                # Asiento:
                # DÉBITO: Costo de Servicios (5.1.1.001)
                # DÉBITO:  ITBIS por Compensar (1.1.4.001)
                # CRÉDITO: Proveedores Locales (2.1.1.001)

                lines = [
                    {
                        "account_id": "5.1.1.001",
                        "account_name": "Costo de Servicios",
                        "debit": base,
                        "credit": 0.0,
                        "description": f"Compra a {third_party}"
                    },
                    {
                        "account_id": "1.1.4.001",
                        "account_name": "ITBIS por Compensar",
                        "debit": itbis_rd,
                        "credit": 0.0,
                        "description": f"ITBIS NCF {invoice_number}"
                    },
                    {
                        "account_id": "2.1.1.001",
                        "account_name": "Proveedores Locales",
                        "debit": 0.0,
                        "credit": total_rd,
                        "description": f"Factura {invoice_number}"
                    }
                ]

                entries.append({
                    "entry_date": invoice_date,
                    "reference": f"GAS-{invoice_number}",
                    "description": f"Factura de Gasto - {third_party}",
                    "lines": lines
                })

        except Exception as e:
            print(f"[TRIAL_BALANCE] Error en gastos: {e}")

        return entries

    def _generate_additional_expense_entries(
        self,
        company_id,
        year:  int,
        month: int
    ) -> List[Dict[str, Any]]:
        """Genera asientos de gastos adicionales acumulativos."""
        entries = []

        try:
            month_str = f"{month:02d}"

            # Obtener conceptos anuales
            concepts = self.controller. get_annual_expense_concepts(
                company_id, year
            ) or []

            for concept_data in concepts:
                concept_name = concept_data.get("concept", "")
                category = concept_data.get("category", "")
                monthly_values = concept_data.get("monthly_values", {})

                # Valor del mes actual
                value_month = float(monthly_values.get(month_str, 0.0) or 0.0)

                # Calcular incremento respecto al mes anterior
                prev_month = month - 1 if month > 1 else 0
                prev_month_str = f"{prev_month:02d}" if prev_month > 0 else None
                
                prev_value = 0.0
                if prev_month_str and prev_month_str in monthly_values:
                    prev_value = float(monthly_values[prev_month_str] or 0.0)

                increment = value_month - prev_value

                if abs(increment) < 0.01:
                    continue  # Sin cambios, no generar asiento

                # Determinar cuenta según categoría
                account_mapping = {
                    "Nómina": ("5.2.1.001", "Sueldos y Salarios"),
                    "Alquiler": ("5.2.1.002", "Alquiler"),
                    "Servicios": ("5.2.1.003", "Servicios Públicos"),
                    "Depreciación": ("5.2.1.004", "Depreciación"),
                    "Ajuste Contable": ("5.2.1.004", "Ajuste de Utilidades"),
                    "Otros": ("5.2.1.004", "Otros Gastos")
                }

                account_id, account_name = account_mapping.get(
                    category,
                    ("5.2.1.004", "Otros Gastos")
                )

                # Asiento:
                # DÉBITO: Gasto correspondiente
                # CRÉDITO:  Nómina por Pagar / Otros Pasivos (2.1.4.001)

                lines = [
                    {
                        "account_id": account_id,
                        "account_name":  account_name,
                        "debit": abs(increment),
                        "credit": 0.0,
                        "description": f"{concept_name} - {category}"
                    },
                    {
                        "account_id": "2.1.4.001",
                        "account_name": "Nómina por Pagar",
                        "debit": 0.0,
                        "credit": abs(increment),
                        "description": f"Provisión {concept_name}"
                    }
                ]

                entry_date = datetime.date(year, month, 1)

                entries.append({
                    "entry_date": entry_date,
                    "reference": f"ADI-{concept_name[: 10]. upper()}",
                    "description": f"Gasto Adicional:  {concept_name}",
                    "lines": lines
                })

        except Exception as e: 
            print(f"[TRIAL_BALANCE] Error en gastos adicionales: {e}")

        return entries

    def calculate_trial_balance(
        self,
        company_id,
        year: int,
        month: int
    ) -> Dict[str, Any]:
        """
        Calcula la balanza de comprobación para el periodo. 

        Returns:
            {
                "accounts": [
                    {
                        "account_id": "1.1.1.001",
                        "account_name": "Caja General",
                        "opening_balance": 0.0,
                        "total_debit": 100000.00,
                        "total_credit": 50000.00,
                        "closing_balance": 50000.00
                    },
                    ... 
                ],
                "totals": {
                    "total_debit": 1000000.00,
                    "total_credit": 1000000.00,
                    "is_balanced": True
                }
            }
        """
        if not self._db:
            return {"accounts": [], "totals": {}}

        try:
            # Obtener plan de cuentas
            accounts = self.controller.get_chart_of_accounts(company_id)

            result_accounts = []
            total_debit = 0.0
            total_credit = 0.0

            for account in accounts:
                account_id = account.get("account_code", "")

                # Obtener saldo del mes
                balance = self.controller.get_account_balance(
                    company_id, account_id, year, month
                )

                opening = balance.get("opening_balance", 0.0)
                debit = balance.get("total_debit", 0.0)
                credit = balance.get("total_credit", 0.0)
                closing = balance.get("closing_balance", 0.0)

                # Solo incluir cuentas con movimiento
                if opening != 0 or debit != 0 or credit != 0:
                    result_accounts.append({
                        "account_id": account_id,
                        "account_name":  account.get("account_name", ""),
                        "account_type": account.get("account_type", ""),
                        "opening_balance": opening,
                        "total_debit":  debit,
                        "total_credit": credit,
                        "closing_balance": closing
                    })

                    total_debit += debit
                    total_credit += credit

            return {
                "accounts": result_accounts,
                "totals":  {
                    "total_debit": total_debit,
                    "total_credit": total_credit,
                    "is_balanced": abs(total_debit - total_credit) < 0.01
                }
            }

        except Exception as e:
            print(f"[TRIAL_BALANCE] Error calculando balanza: {e}")
            return {"accounts": [], "totals": {}}