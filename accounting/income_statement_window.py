from __future__ import annotations

import calendar
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QComboBox,
    QMessageBox,
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QPalette


class IncomeStatementWindow(QDialog):
    """
    Estado de Resultados (P&L - Profit & Loss).

    Muestra:
    - Ingresos Operacionales (Solo contabilidad)
    - Costo de Ventas
    - Utilidad Bruta
    - Gastos Operacionales
    - Gastos Financieros
    - Gastos Adicionales (sistema acumulativo anual)
    - Utilidad Neta
    """

    MONTHS_MAP = {
        "Enero": "01", "Febrero": "02", "Marzo": "03", "Abril": "04",
        "Mayo": "05", "Junio": "06", "Julio": "07", "Agosto": "08",
        "Septiembre": "09", "Octubre": "10", "Noviembre": "11", "Diciembre": "12",
    }

    def __init__(
        self,
        parent,
        controller,
        company_id,
        company_name: str,
        month_str: str,
        year_int: int,
    ):
        super().__init__(parent)
        self.controller = controller
        self.company_id = company_id
        self.company_name = company_name
        self.current_month_str = month_str
        self.current_year_int = year_int

        self.setWindowTitle(f"Estado de Resultados - {company_name}")
        self.resize(1000, 700)
        self.setModal(True)

        self._build_ui()
        self._load_statement()

    # =========================
    # UI
    # =========================
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # === HEADER ===
        header_card = QFrame()
        header_card.setObjectName("headerCard")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setSpacing(12)

        title = QLabel("📈 Estado de Resultados")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A;")
        title_row.addWidget(title)
        title_row.addStretch()

        # Selectores de periodo
        lbl_mes = QLabel("Mes:")
        lbl_mes.setStyleSheet("font-weight: 600; color: #475569;")
        title_row.addWidget(lbl_mes)

        self.month_selector = QComboBox()
        self.month_selector.setObjectName("modernCombo")
        for month in self.MONTHS_MAP.keys():
            self.month_selector.addItem(month)
        self.month_selector.currentIndexChanged.connect(self._on_period_changed)
        title_row.addWidget(self.month_selector)

        lbl_ano = QLabel("Año:")
        lbl_ano.setStyleSheet("font-weight: 600; color: #475569;")
        title_row.addWidget(lbl_ano)

        self.year_selector = QComboBox()
        self.year_selector.setObjectName("modernCombo")
        self.year_selector.currentIndexChanged.connect(self._on_period_changed)
        title_row.addWidget(self.year_selector)

        # Botón refrescar
        self.btn_refresh = QPushButton("🔃 Refrescar")
        self.btn_refresh.setObjectName("refreshButton")
        self.btn_refresh.clicked.connect(self._load_statement)

        self.btn_refresh.setMinimumWidth(140)
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        title_row.addWidget(self.btn_refresh)

        header_layout.addLayout(title_row)

        # Subtítulo
        self.subtitle_label = QLabel(f"{self.company_name}")
        self.subtitle_label.setStyleSheet("font-size: 12px; color: #64748B;")
        header_layout.addWidget(self.subtitle_label)

        root.addWidget(header_card)

        # === ÁRBOL DEL ESTADO ===
        self.tree = QTreeWidget()
        self.tree.setObjectName("statementTree")
        self.tree.setHeaderLabels(["Cuenta", "Monto"])
        self.tree.setColumnWidth(0, 700)
        self.tree.setColumnWidth(1, 250)
        self.tree.setAlternatingRowColors(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(20)

        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)

        # Forzar palette claro
        pal = self.tree.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#F9FAFB"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#0F172A"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#0F172A"))
        self.tree.setPalette(pal)

        root.addWidget(self.tree)

        # === UTILIDAD NETA ===
        result_card = QFrame()
        result_card.setObjectName("resultCard")
        result_layout = QHBoxLayout(result_card)
        result_layout.setContentsMargins(24, 20, 24, 20)
        result_layout.setSpacing(16)

        result_lbl = QLabel("UTILIDAD NETA:")
        result_lbl.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #1E293B; letter-spacing: 0.5px;"
        )

        self.result_value = QLabel("RD$ 0.00")
        self.result_value.setStyleSheet(
            "font-size: 28px; font-weight: 800; color: #1D4ED8;"
        )

        result_layout.addWidget(result_lbl)
        result_layout.addWidget(self.result_value)
        result_layout.addStretch()

        root.addWidget(result_card)

        # === ESTILOS ===
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }

            QFrame#headerCard {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }

            QFrame#resultCard {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 2px solid #15803D;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #F0FDF4,
                    stop:1 #FFFFFF
                );
            }

            QComboBox#modernCombo {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 12px;
                color: #0F172A;
                font-size: 13px;
                min-width: 120px;
            }
            QComboBox#modernCombo:hover { border-color: #3B82F6; }

            QPushButton#refreshButton {
                background-color: #64748B;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                min-width: 140px;
                height: 34px;
                padding: 0px 14px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton#refreshButton:hover {
                background-color: #475569;
            }

            QTreeWidget#statementTree {
                background-color: #FFFFFF;
                alternate-background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                color: #0F172A;
                font-size: 13px;
            }

            QTreeWidget#statementTree::item {
                padding: 8px;
                border: none;
                background-color: #FFFFFF;
                color: #0F172A;
            }

            QTreeWidget#statementTree::item:alternate {
                background-color: #F9FAFB;
            }

            QTreeWidget#statementTree::item:selected {
                background-color: #EFF6FF;
                color: #1E293B;
            }

            QHeaderView::section {
                background-color: #F1F5F9;
                border: none;
                padding: 10px 8px;
                color: #475569;
                font-weight: 700;
                font-size: 12px;
            }
        """)

        # Inicializar selectores
        self._init_period_selectors()

    # =========================
    # Periodo
    # =========================
    def _init_period_selectors(self):
        """Inicializa los selectores de periodo."""
        month_name = None
        for name, code in self.MONTHS_MAP.items():
            if code == self.current_month_str:
                month_name = name
                break

        if month_name:
            idx = list(self.MONTHS_MAP.keys()).index(month_name)
            self.month_selector.setCurrentIndex(idx)

        self.year_selector.clear()
        base_year = self.current_year_int
        years = [base_year - 1, base_year, base_year + 1]
        for y in years:
            self.year_selector.addItem(str(y))

        try:
            idx_y = years.index(base_year)
            self.year_selector.setCurrentIndex(idx_y)
        except ValueError:
            self.year_selector.setCurrentIndex(1)

        self._update_subtitle()

    def _update_subtitle(self):
        """Actualiza el subtítulo con el periodo."""
        month_name = self.month_selector.currentText()
        year = self.year_selector.currentText()
        self.subtitle_label.setText(f"{self.company_name} - {month_name} {year}")

    def _on_period_changed(self):
        """Maneja cambio de periodo."""
        month_name = self.month_selector.currentText()
        self.current_month_str = self.MONTHS_MAP.get(month_name, "01")

        try:
            self.current_year_int = int(self.year_selector.currentText())
        except Exception:
            self.current_year_int = QDate.currentDate().year()

        self._update_subtitle()
        self._load_statement()

    # =========================
    # Carga del Estado
    # =========================
    def _load_statement(self):
        """Carga el estado de resultados usando SOLO datos contables (evita duplicidad)."""
        self.tree.clear()

        try:
            # ✅ CORRECCIÓN CRÍTICA:
            # Eliminamos la lectura de "facturas" (summary de get_itbis_month_summary)
            # para no sumar doble. El estado de resultados debe basarse 
            # estrictamente en los saldos del Plan de Cuentas.

            # 1. Cargar Plan de Cuentas
            accounts = []
            if hasattr(self.controller, "get_chart_of_accounts"):
                accounts = self.controller.get_chart_of_accounts(self.company_id) or []

            # 2. Filtrar cuentas por tipo
            ingresos_cuentas = [a for a in accounts if a.get("account_type") == "INGRESO"]
            gastos_cuentas = [a for a in accounts if a.get("account_type") == "GASTO"]

            # 3. Clasificar gastos por categoría
            costo_ventas = [g for g in gastos_cuentas if g.get("category") == "COSTO_VENTAS"]
            
            # Ampliar categorías de gastos operacionales
            gastos_operacionales = [g for g in gastos_cuentas if g.get("category") in (
                "GASTO_OPERACIONAL", "GASTO_ADMINISTRATIVO", "GASTO_VENTAS"
            )]
            
            gastos_financieros = [g for g in gastos_cuentas if g.get("category") == "GASTO_FINANCIERO"]

            # 4. Calcular saldos (Suma de cuentas contables)
            total_ingresos = self._sum_accounts(ingresos_cuentas)
            total_costo = self._sum_accounts(costo_ventas)
            total_gastos_op = self._sum_accounts(gastos_operacionales)
            total_gastos_fin = self._sum_accounts(gastos_financieros)

            # 5. Gastos Adicionales (Módulo externo no contable)
            total_gastos_adicionales = 0.0
            if hasattr(self.controller, "get_expense_value_for_month"):
                try:
                    total_gastos_adicionales = self.controller.get_expense_value_for_month(
                        self.company_id,
                        self.current_year_int,
                        self.current_month_str
                    )
                except Exception as e:
                    print(f"[INCOME_STMT] Error gastos adicionales: {e}")

            # === CONSTRUIR ÁRBOL ===
            self._add_section_item("INGRESOS OPERACIONALES", total_ingresos, "#15803D")

            utilidad_bruta = total_ingresos - total_costo
            if total_costo > 0:
                self._add_section_item("(-) COSTO DE VENTAS", total_costo, "#DC2626")
            
            self._add_subtotal("UTILIDAD BRUTA", utilidad_bruta, "#1E40AF")

            if total_gastos_op > 0:
                self._add_section_item("(-) GASTOS OPERACIONALES", total_gastos_op, "#DC2626")

            if total_gastos_fin > 0:
                self._add_section_item("(-) GASTOS FINANCIEROS", total_gastos_fin, "#DC2626")

            if total_gastos_adicionales > 0:
                self._add_additional_expenses_section_detailed(total_gastos_adicionales)

            # Utilidad Neta
            utilidad_neta = utilidad_bruta - total_gastos_op - total_gastos_fin - total_gastos_adicionales

            self._add_subtotal(
                "UTILIDAD NETA",
                utilidad_neta,
                "#15803D" if utilidad_neta >= 0 else "#DC2626",
                bold=True,
                size=14
            )

            color = "#15803D" if utilidad_neta >= 0 else "#DC2626"
            prefix = "✅ " if utilidad_neta >= 0 else "⚠️ "
            self.result_value.setText(f"{prefix}RD$ {utilidad_neta:,.2f}")
            self.result_value.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {color};")

            self.tree.expandAll()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando estado:\n{e}")
            import traceback
            traceback.print_exc()

    def _sum_accounts(self, accounts: list) -> float:
        """Suma los saldos de una lista de cuentas."""
        total = 0.0
        for acc in accounts:
            if not acc.get("is_detail", False):
                continue
            total += self._get_account_balance(acc)
        return total

    def _add_section_item(self, title: str, amount: float, color: str):
        """Agrega una línea simple de sección."""
        item = QTreeWidgetItem(self.tree)
        item.setText(0, title)
        item.setText(1, f"RD$ {amount:,.2f}")
        item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        item.setFont(0, font)
        item.setFont(1, font)
        item.setForeground(0, QColor(color))
        item.setForeground(1, QColor(color))

    def _add_subtotal(self, label: str, amount: float, color: str, bold: bool = True, size: int = 12):
        """Agrega una línea de subtotal."""
        item = QTreeWidgetItem(self.tree)
        item.setText(0, label)
        item.setText(1, f"RD$ {amount:,.2f}")
        item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        font = QFont()
        if bold:
            font.setBold(True)
        font.setPointSize(size)

        item.setFont(0, font)
        item.setFont(1, font)
        item.setForeground(0, QColor(color))
        item.setForeground(1, QColor(color))
        item.setBackground(0, QColor("#F1F5F9"))
        item.setBackground(1, QColor("#F1F5F9"))

    def _add_additional_expenses_section_detailed(self, total: float):
        """Agrega sección de gastos adicionales con detalle de conceptos."""
        root_item = QTreeWidgetItem(self.tree)
        root_item.setText(0, "(-) GASTOS ADICIONALES (No Facturados)")

        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        root_item.setFont(0, font)
        root_item.setForeground(0, QColor("#EA580C"))

        concepts = []
        if hasattr(self.controller, "get_annual_expense_concepts"):
            try:
                concepts = self.controller.get_annual_expense_concepts(
                    self.company_id,
                    self.current_year_int
                ) or []
            except Exception:
                concepts = []

        for concept_data in concepts:
            concept_name = concept_data.get("concept", "")
            monthly_values = concept_data.get("monthly_values", {})

            value = float(monthly_values.get(self.current_month_str, 0.0) or 0.0)

            # Si el valor es 0, buscar mes anterior (comportamiento acumulativo)
            if value == 0.0:
                month_int = int(self.current_month_str)
                for m in range(month_int - 1, 0, -1):
                    m_str = f"{m:02d}"
                    if m_str in monthly_values:
                        value = float(monthly_values[m_str] or 0.0)
                        break

            if value == 0.0:
                continue

            item = QTreeWidgetItem(root_item)
            item.setText(0, f"  • {concept_name}")
            item.setText(1, f"RD$ {value:,.2f}")
            item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setForeground(0, QColor("#64748B"))
            item.setForeground(1, QColor("#64748B"))

        root_item.setText(1, f"RD$ {total:,.2f}")
        root_item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        root_item.setFont(1, font)
        root_item.setForeground(1, QColor("#EA580C"))

    def _get_account_balance(self, account: dict) -> float:
        """Obtiene el saldo de una cuenta."""
        if not account.get("is_detail", False):
            return 0.0

        account_code = account.get("account_code", "")
        account_type = account.get("account_type", "")

        if not account_type:
            first_digit = account_code[0] if account_code else ""
            if first_digit == "4":
                account_type = "INGRESO"
            elif first_digit == "5":
                account_type = "GASTO"

        try:
            if hasattr(self.controller, "get_account_balance"):
                balance_data = self.controller.get_account_balance(
                    self.company_id,
                    account_code,
                    self.current_year_int,
                    int(self.current_month_str)
                )

                closing = float(balance_data.get("closing_balance", 0.0))

                # Para ingresos, el saldo acreedor es positivo para el reporte
                if account_type == "INGRESO":
                    closing = -closing

                return closing
        except Exception as e:
            print(f"[INCOME_STMT] Error obteniendo saldo de {account_code}: {e}")

        return 0.0