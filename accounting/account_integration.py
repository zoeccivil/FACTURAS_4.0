"""
account_integration.py
Integración automática de facturas con asientos contables
"""

from typing import Optional, Tuple
import datetime


class AccountIntegration:
    """
    Maneja la integración automática entre facturas y asientos contables. 
    """

    # Mapeo de cuentas estándar
    DEFAULT_ACCOUNTS = {
        # Activos
        "cash": "1.1.1.001",              # Caja General
        "accounts_receivable": "1.1.2.001",  # Cuentas por Cobrar
        "itbis_adelantado": "1.1.3.001",   # ITBIS Adelantado
        
        # Pasivos
        "accounts_payable": "2.1.1.001",   # Cuentas por Pagar
        "itbis_por_pagar": "2.1.4.001",    # ITBIS por Pagar
        
        # Ingresos
        "income_services": "4.1.1.001",    # Ingresos por Servicios
        "income_sales": "4.1.1.002",       # Ventas
        
        # Gastos
        "cost_of_sales": "5.1.1.001",      # Costo de Ventas
        "operating_expense": "5.2.1.001",   # Gastos Operacionales
        "supplies": "5.2.1.002",           # Efectos de Consumo
        "services": "5.2.1.003",           # Servicios Contratados
        "rent": "5.2.1.004",               # Arrendamientos
    }

    def __init__(self, controller):
        """
        Args:
            controller: Instancia del controlador (LogicControllerFirebase)
        """
        self.controller = controller

    def create_journal_entry(
        self,
        company_id,
        entry_date,
        reference:  str,
        description: str,
        lines: list[dict]
    ) -> tuple[bool, str]:
        """
        Crea un asiento contable y actualiza los saldos de las cuentas.
        
        Args:
            company_id: ID de la empresa
            entry_date: Fecha del asiento (datetime. date o str)
            reference: Referencia/número del asiento
            description:  Descripción del asiento
            lines: Lista de líneas del asiento con formato: 
                [
                    {
                        "account_id": "1. 1.1.001",
                        "account_name": "Caja General",
                        "debit":  1000.0,
                        "credit": 0.0,
                        "description": "Descripción de la línea"
                    },
                    ...
                ]
        
        Returns:
            tuple[bool, str]: (éxito, mensaje)
        """
        if not self._db:
            return False, "Base de datos no inicializada."

        try:
            normalized_id = self._normalize_company_id(company_id)
            
            # Convertir fecha a datetime. datetime
            if isinstance(entry_date, str):
                entry_date = datetime.datetime.strptime(entry_date, "%Y-%m-%d")
            elif isinstance(entry_date, datetime. date) and not isinstance(entry_date, datetime.datetime):
                entry_date = datetime.datetime. combine(entry_date, datetime. time())
            
            # Validar mínimo 2 líneas
            if not lines or len(lines) < 2:
                return False, "El asiento debe tener al menos 2 líneas."
            
            # Calcular totales
            total_debit = sum(float(line.get("debit", 0)) for line in lines)
            total_credit = sum(float(line.get("credit", 0)) for line in lines)
            
            # Validar cuadratura (con tolerancia de 0.01)
            if abs(total_debit - total_credit) >= 0.01:
                return False, f"Asiento descuadrado: Débito={total_debit: ,.2f}, Crédito={total_credit:,.2f}"
            
            # Generar ID único para el asiento
            import uuid
            entry_id = f"JE-{entry_date.year}-{str(uuid.uuid4())[:8].upper()}"
            period = f"{entry_date.year}-{entry_date. month:02d}"
            
            # Construir documento del asiento
            entry_data = {
                "entry_id":  entry_id,
                "company_id": normalized_id,
                "entry_date": entry_date,
                "period": period,
                "year": entry_date.year,
                "month": entry_date.month,
                "reference": reference or "",
                "description": description,
                "lines": [
                    {
                        "line_number": idx + 1,
                        "account_id": line.get("account_id", ""),
                        "account_name": line. get("account_name", ""),
                        "debit": float(line.get("debit", 0)),
                        "credit": float(line.get("credit", 0)),
                        "description": line.get("description", ""),
                    }
                    for idx, line in enumerate(lines)
                ],
                "total_debit": total_debit,
                "total_credit": total_credit,
                "is_balanced": True,
                "status": "POSTED",
                "created_by": "system",
                "created_at": self._get_timestamp(),
                "posted_at": self._get_timestamp(),
            }
            
            # Guardar asiento en Firestore
            self._db.collection("journal_entries").add(entry_data)
            print(f"[JOURNAL_ENTRY] ✅ Asiento {entry_id} creado")
            
            # ✅ ACTUALIZAR SALDOS DE CUENTAS
            self._update_account_balances(normalized_id, entry_date.year, entry_date. month, lines)
            
            return True, f"Asiento {entry_id} creado correctamente."

        except Exception as e:
            print(f"[JOURNAL_ENTRY] ❌ Error:  {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error al crear asiento: {e}"
        

    def _create_entry_for_income_invoice(
        self,
        company_id: str,
        invoice_data: dict
    ) -> Tuple[bool, str, Optional[str]]: 
        """Crea asiento para factura emitida (ingreso)."""
        
        # Extraer datos
        invoice_number = invoice_data.get("invoice_number", "")
        invoice_date = invoice_data.get("invoice_date")
        third_party = invoice_data.get("third_party_name", "Cliente")
        subtotal = float(invoice_data.get("subtotal", 0.0))
        itbis = float(invoice_data.get("itbis", 0.0))
        total = float(invoice_data.get("total", 0.0))

        # Validar
        if total <= 0:
            return False, "Total de factura inválido", None

        # Convertir fecha
        if isinstance(invoice_date, str):
            try:
                invoice_date = datetime.datetime.strptime(invoice_date[: 10], "%Y-%m-%d")
            except:
                invoice_date = datetime.datetime.now()
        elif not isinstance(invoice_date, datetime. datetime):
            invoice_date = datetime.datetime.now()

        # Obtener cuentas
        accounts = self._get_accounts_for_income(company_id)
        if not accounts:
            return False, "No se encontraron cuentas configuradas para ingresos", None

        # Construir líneas del asiento
        lines = []

        # DÉBITO: Caja General o Cuentas por Cobrar
        cash_account = accounts. get("cash") or accounts.get("accounts_receivable")
        if not cash_account:
            return False, "No se encontró cuenta de Caja o Cuentas por Cobrar", None

        lines.append({
            "account_id": cash_account["account_code"],
            "account_name":  cash_account["account_name"],
            "description": f"Cobro factura {invoice_number} - {third_party}",
            "debit": total,
            "credit": 0.0
        })

        # CRÉDITO: Ingresos por Servicios/Ventas
        income_account = accounts.get("income")
        if not income_account: 
            return False, "No se encontró cuenta de Ingresos", None

        lines.append({
            "account_id": income_account["account_code"],
            "account_name": income_account["account_name"],
            "description": f"Venta factura {invoice_number}",
            "debit": 0.0,
            "credit": subtotal
        })

        # CRÉDITO: ITBIS por Pagar (si hay ITBIS)
        if itbis > 0:
            itbis_account = accounts.get("itbis_por_pagar")
            if itbis_account:
                lines.append({
                    "account_id": itbis_account["account_code"],
                    "account_name": itbis_account["account_name"],
                    "description": f"ITBIS factura {invoice_number}",
                    "debit":  0.0,
                    "credit": itbis
                })

        # Crear asiento
        entry_data = {
            "company_id": company_id,
            "entry_date": invoice_date,
            "reference":  f"FACT-{invoice_number}",
            "description": f"Factura emitida #{invoice_number} - {third_party}",
            "lines": lines,
            "status": "POSTED",
            "source":  "INVOICE_INCOME",
            "source_id": invoice_number
        }

        return self._save_journal_entry(entry_data)

    def _create_entry_for_expense_invoice(
        self,
        company_id: str,
        invoice_data: dict
    ) -> Tuple[bool, str, Optional[str]]: 
        """Crea asiento para factura de gasto."""
        
        # Extraer datos
        invoice_number = invoice_data.get("invoice_number", "")
        invoice_date = invoice_data.get("invoice_date")
        third_party = invoice_data.get("third_party_name", "Proveedor")
        subtotal = float(invoice_data.get("subtotal", 0.0))
        itbis = float(invoice_data.get("itbis", 0.0))
        total = float(invoice_data.get("total", 0.0))

        # Validar
        if total <= 0:
            return False, "Total de factura inválido", None

        # Convertir fecha
        if isinstance(invoice_date, str):
            try:
                invoice_date = datetime.datetime. strptime(invoice_date[: 10], "%Y-%m-%d")
            except:
                invoice_date = datetime.datetime.now()
        elif not isinstance(invoice_date, datetime.datetime):
            invoice_date = datetime.datetime.now()

        # Obtener cuentas
        accounts = self._get_accounts_for_expense(company_id)
        if not accounts:
            return False, "No se encontraron cuentas configuradas para gastos", None

        # Construir líneas del asiento
        lines = []

        # DÉBITO:  Gastos Operacionales
        expense_account = accounts.get("expense")
        if not expense_account:
            return False, "No se encontró cuenta de Gastos", None

        lines.append({
            "account_id": expense_account["account_code"],
            "account_name": expense_account["account_name"],
            "description": f"Gasto factura {invoice_number} - {third_party}",
            "debit": subtotal,
            "credit": 0.0
        })

        # DÉBITO: ITBIS Adelantado (si hay ITBIS)
        if itbis > 0:
            itbis_account = accounts.get("itbis_adelantado")
            if itbis_account:
                lines.append({
                    "account_id": itbis_account["account_code"],
                    "account_name": itbis_account["account_name"],
                    "description": f"ITBIS adelantado factura {invoice_number}",
                    "debit": itbis,
                    "credit": 0.0
                })

        # CRÉDITO: Caja General o Cuentas por Pagar
        cash_account = accounts.get("cash") or accounts.get("accounts_payable")
        if not cash_account:
            return False, "No se encontró cuenta de Caja o Cuentas por Pagar", None

        lines. append({
            "account_id": cash_account["account_code"],
            "account_name":  cash_account["account_name"],
            "description": f"Pago factura {invoice_number} - {third_party}",
            "debit": 0.0,
            "credit": total
        })

        # Crear asiento
        entry_data = {
            "company_id":  company_id,
            "entry_date": invoice_date,
            "reference": f"FACT-{invoice_number}",
            "description": f"Factura de gasto #{invoice_number} - {third_party}",
            "lines": lines,
            "status": "POSTED",
            "source": "INVOICE_EXPENSE",
            "source_id": invoice_number
        }

        return self._save_journal_entry(entry_data)

    def _get_accounts_for_income(self, company_id: str) -> dict:
        """Obtiene las cuentas necesarias para factura de ingreso."""
        accounts = {}
        
        all_accounts = self.controller.get_chart_of_accounts(company_id) or []
        
        # Buscar cuentas por código
        for acc in all_accounts:
            code = acc.get("account_code", "")
            
            if code == self.DEFAULT_ACCOUNTS["cash"]:
                accounts["cash"] = acc
            elif code == self.DEFAULT_ACCOUNTS["accounts_receivable"]:
                accounts["accounts_receivable"] = acc
            elif code == self.DEFAULT_ACCOUNTS["income_services"]:
                accounts["income"] = acc
            elif code == self.DEFAULT_ACCOUNTS["income_sales"]:
                if "income" not in accounts:  # Usar como fallback
                    accounts["income"] = acc
            elif code == self.DEFAULT_ACCOUNTS["itbis_por_pagar"]:
                accounts["itbis_por_pagar"] = acc
        
        return accounts

    def _get_accounts_for_expense(self, company_id: str) -> dict:
        """Obtiene las cuentas necesarias para factura de gasto."""
        accounts = {}
        
        all_accounts = self.controller.get_chart_of_accounts(company_id) or []
        
        # Buscar cuentas por código
        for acc in all_accounts:
            code = acc.get("account_code", "")
            
            if code == self.DEFAULT_ACCOUNTS["cash"]:
                accounts["cash"] = acc
            elif code == self.DEFAULT_ACCOUNTS["accounts_payable"]:
                accounts["accounts_payable"] = acc
            elif code == self.DEFAULT_ACCOUNTS["operating_expense"]:
                accounts["expense"] = acc
            elif code == self.DEFAULT_ACCOUNTS["supplies"]:
                if "expense" not in accounts:  # Usar como fallback
                    accounts["expense"] = acc
            elif code == self.DEFAULT_ACCOUNTS["itbis_adelantado"]: 
                accounts["itbis_adelantado"] = acc
        
        return accounts

    def _save_journal_entry(self, entry_data: dict) -> Tuple[bool, str, Optional[str]]:
        """Guarda el asiento contable."""
        try:
            if hasattr(self.controller, "create_journal_entry"):
                result = self.controller.create_journal_entry(entry_data)
                
                if isinstance(result, tuple):
                    ok, msg = result
                    entry_id = None
                else:
                    ok = bool(result)
                    msg = "Asiento creado" if ok else "Error creando asiento"
                    entry_id = result if ok else None
                
                return ok, msg, entry_id
            else:
                return False, "Método create_journal_entry no disponible", None

        except Exception as e:
            return False, f"Error guardando asiento: {e}", None

    def update_journal_entry_from_invoice(
        self,
        company_id: str,
        invoice_number: str,
        invoice_data: dict,
        invoice_type: str
    ) -> Tuple[bool, str]: 
        """
        Actualiza el asiento contable asociado a una factura.
        
        Strategy:  Eliminar asiento anterior y crear uno nuevo. 
        """
        try:
            # Eliminar asiento anterior
            self. delete_journal_entry_from_invoice(company_id, invoice_number)
            
            # Crear nuevo asiento
            ok, msg, entry_id = self.create_journal_entry_from_invoice(
                company_id,
                invoice_data,
                invoice_type
            )
            
            return ok, msg

        except Exception as e:
            return False, f"Error actualizando asiento: {e}"

    def delete_journal_entry_from_invoice(
        self,
        company_id: str,
        invoice_number: str
    ) -> Tuple[bool, str]:
        """Elimina el asiento contable asociado a una factura."""
        try:
            reference = f"FACT-{invoice_number}"
            
            # Buscar asiento por referencia
            if hasattr(self.controller, "get_journal_entries"):
                entries = self.controller.get_journal_entries(
                    company_id,
                    limit=1000
                ) or []
                
                for entry in entries:
                    if entry.get("reference") == reference:
                        entry_id = entry.get("id")
                        
                        if hasattr(self.controller, "delete_journal_entry"):
                            ok, msg = self.controller. delete_journal_entry(entry_id)
                            return ok, msg
                
                return True, "No se encontró asiento asociado"
            
            return True, "Función de búsqueda no disponible"

        except Exception as e:
            return False, f"Error eliminando asiento: {e}"