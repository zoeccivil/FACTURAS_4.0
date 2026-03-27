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
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QPalette


class BalanceSheetWindow(QDialog):
    """
    Balance General (Estado de Situación Financiera).

    Muestra:
    - Activos (Corrientes y No Corrientes)
    - Pasivos (Corrientes y No Corrientes)
    - Patrimonio
    - Verificación: Activos = Pasivos + Patrimonio
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

        self.setWindowTitle(f"Balance General - {company_name}")
        self.resize(1000, 700)
        self.setModal(True)

        self._build_ui()
        self._load_balance()

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

        title = QLabel("💰 Balance General")
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
        self.btn_refresh.clicked.connect(self._load_balance)
        title_row.addWidget(self.btn_refresh)

        # ✅ BOTÓN RECALCULAR SALDOS
        self.btn_recalc = QPushButton("🔄 Recalcular Saldos")
        self.btn_recalc.setObjectName("recalcButton")
        self.btn_recalc.clicked.connect(self._recalculate_balances)
        title_row.addWidget(self.btn_recalc)

        header_layout.addLayout(title_row)

        # Subtítulo
        self.subtitle_label = QLabel(f"{self.company_name}")
        self.subtitle_label.setStyleSheet("font-size: 12px; color: #64748B;")
        header_layout.addWidget(self.subtitle_label)

        root.addWidget(header_card)

        # === ÁRBOL DEL BALANCE ===
        self.tree = QTreeWidget()
        self.tree.setObjectName("balanceTree")
        self.tree.setHeaderLabels(["Cuenta", "Saldo"])
        self.tree.setColumnWidth(0, 700)
        self.tree.setColumnWidth(1, 250)
        self.tree.setAlternatingRowColors(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(20)

        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)

        # 🔥 Forzar palette claro (por si hay tema global oscuro)
        pal = self.tree.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#F9FAFB"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#0F172A"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#0F172A"))
        self.tree.setPalette(pal)

        root.addWidget(self.tree)

        # === VERIFICACIÓN ===
        verify_card = QFrame()
        verify_card.setObjectName("verifyCard")
        verify_layout = QHBoxLayout(verify_card)
        verify_layout.setContentsMargins(20, 16, 20, 16)
        verify_layout.setSpacing(12)

        verify_lbl = QLabel("VERIFICACIÓN:")
        verify_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #1E293B;")
        verify_layout.addWidget(verify_lbl)

        self.verify_status = QLabel("⏳ Calculando...")
        self.verify_status.setStyleSheet("font-size: 14px; font-weight: 700; color: #64748B;")
        verify_layout.addWidget(self.verify_status)

        verify_layout.addStretch()
        root.addWidget(verify_card)

        # === ESTILOS ===
        # ✅ Correcciones:
        # - QComboBox#modernCombo:hover (antes tenía ": hover")
        # - QHeaderView::section (antes tenía ":: section")
        # - Forzar colores de filas: ::item y ::item:alternate
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }

            QFrame#headerCard, QFrame#verifyCard {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }

            QFrame#verifyCard {
                border: 2px solid #3B82F6;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #EFF6FF,
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

            QPushButton#refreshButton, QPushButton#recalcButton {
                background-color: #64748B;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0px 16px;
                font-weight: 600;
                font-size: 14px;
                height: 32px;
            }
            QPushButton#refreshButton:hover, QPushButton#recalcButton:hover {
                background-color: #475569;
            }

            QPushButton#recalcButton {
                background-color: #EA580C;
            }
            QPushButton#recalcButton:hover {
                background-color: #C2410C;
            }

            /* === TREE (FIX TEMA OSCURO) === */
            QTreeWidget#balanceTree {
                background-color: #FFFFFF;
                alternate-background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                color: #0F172A;
                font-size: 13px;
            }

            QTreeWidget#balanceTree::item {
                padding: 8px;
                border: none;
                background-color: #FFFFFF;
                color: #0F172A;
            }

            QTreeWidget#balanceTree::item:alternate {
                background-color: #F9FAFB;
            }

            QTreeWidget#balanceTree::item:selected {
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

            /* === QMESSAGEBOX === */
            QMessageBox {
                background-color: #FFFFFF;
            }
            QMessageBox QLabel {
                color: #0F172A;
                font-size: 13px;
                background-color: transparent;
            }
            QMessageBox QPushButton {
                background-color: #1E293B;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 6px 16px;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #334155;
            }
        """)

        # Inicializar selectores
        self._init_period_selectors()

    # =========================
    # Periodo
    # =========================
    def _init_period_selectors(self):
        """Inicializa los selectores de periodo."""
        # Mes
        month_name = None
        for name, code in self.MONTHS_MAP.items():
            if code == self.current_month_str:
                month_name = name
                break

        if month_name:
            idx = list(self.MONTHS_MAP.keys()).index(month_name)
            self.month_selector.setCurrentIndex(idx)

        # Año
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
        self.subtitle_label.setText(
            f"{self.company_name} - Al {self._get_last_day_of_month()} de {month_name} {year}"
        )

    def _get_last_day_of_month(self) -> int:
        """Obtiene el último día del mes actual."""
        month_name = self.month_selector.currentText()
        month_int = int(self.MONTHS_MAP.get(month_name, "01"))
        try:
            year_int = int(self.year_selector.currentText())
        except Exception:
            year_int = QDate.currentDate().year()

        return calendar.monthrange(year_int, month_int)[1]

    def _on_period_changed(self):
        """Maneja cambio de periodo."""
        month_name = self.month_selector.currentText()
        self.current_month_str = self.MONTHS_MAP.get(month_name, "01")

        try:
            self.current_year_int = int(self.year_selector.currentText())
        except Exception:
            self.current_year_int = QDate.currentDate().year()

        self._update_subtitle()
        self._load_balance()

    # =========================
    # Recalculo
    # =========================
    def _recalculate_balances(self):
        """Recalcula todos los saldos del año actual."""
        reply = QMessageBox.question(
            self,
            "Recalcular Saldos",
            f"¿Recalcular todos los saldos del año {self.current_year_int}?\n\n"
            "Esto recreará los saldos basándose en los asientos existentes.\n\n"
            "⚠️ Todos los saldos del año se recalcularán desde cero.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if hasattr(self.controller, "recalculate_all_balances"):
                    ok, msg = self.controller.recalculate_all_balances(
                        self.company_id,
                        self.current_year_int,
                    )

                    if ok:
                        QMessageBox.information(self, "Éxito", msg)
                        self._load_balance()
                    else:
                        QMessageBox.warning(self, "Error", msg)
                else:
                    QMessageBox.critical(
                        self,
                        "Error",
                        "Método recalculate_all_balances no implementado en el controller.",
                    )

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error recalculando:\n{e}")
                import traceback
                traceback.print_exc()

    # =========================
    # Carga del Balance
    # =========================
    def _load_balance(self):
        """Carga el balance general."""
        self.tree.clear()

        try:
            if not hasattr(self.controller, "get_chart_of_accounts"):
                QMessageBox.critical(self, "Error", "Método get_chart_of_accounts no implementado.")
                return

            # Obtener todas las cuentas
            accounts = self.controller.get_chart_of_accounts(self.company_id) or []

            if not accounts:
                QMessageBox.information(
                    self,
                    "Sin Cuentas",
                    "No hay plan de cuentas disponible.\n\n"
                    "Inicializa el plan de cuentas desde el menú Contabilidad.",
                )
                return

            # Separar por tipo
            activos = [a for a in accounts if a.get("account_type") == "ACTIVO"]
            pasivos = [a for a in accounts if a.get("account_type") == "PASIVO"]
            patrimonio = [a for a in accounts if a.get("account_type") == "PATRIMONIO"]

            # Construir árbol
            total_activos = self._build_section("ACTIVOS", activos, "#15803D")
            total_pasivos = self._build_section("PASIVOS", pasivos, "#DC2626")
            total_patrimonio = self._build_section("PATRIMONIO", patrimonio, "#3B82F6")

            # Total Pasivo + Patrimonio
            item_total_pp = QTreeWidgetItem(self.tree)
            item_total_pp.setText(0, "TOTAL PASIVO + PATRIMONIO")
            item_total_pp.setText(1, f"RD$ {total_pasivos + total_patrimonio:,.2f}")

            font = QFont()
            font.setBold(True)
            font.setPointSize(11)
            item_total_pp.setFont(0, font)
            item_total_pp.setFont(1, font)
            item_total_pp.setForeground(0, QColor("#1E293B"))
            item_total_pp.setForeground(1, QColor("#1E293B"))
            item_total_pp.setBackground(0, QColor("#F1F5F9"))
            item_total_pp.setBackground(1, QColor("#F1F5F9"))

            self.tree.expandAll()

            # Verificación
            self._verify_balance(total_activos, total_pasivos + total_patrimonio)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando balance:\n{e}")
            import traceback
            traceback.print_exc()

    def _build_section(self, title: str, accounts: list, color: str) -> float:
        """Construye una sección del balance (ACTIVOS, PASIVOS, PATRIMONIO)."""
        # Crear item raíz
        root_item = QTreeWidgetItem(self.tree)
        root_item.setText(0, title)

        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        root_item.setFont(0, font)
        root_item.setForeground(0, QColor(color))

        # Organizar cuentas por jerarquía
        accounts_dict = {a["account_code"]: a for a in accounts}
        root_accounts = [a for a in accounts if not a.get("parent_account")]

        total_section = 0.0

        for acc in sorted(root_accounts, key=lambda x: x["account_code"]):
            subtotal = self._add_account_item(root_item, acc, accounts_dict, color)
            total_section += subtotal

        # Agregar total
        root_item.setText(1, f"RD$ {total_section:,.2f}")
        root_item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        root_item.setFont(1, font)
        root_item.setForeground(1, QColor(color))

        return total_section

    def _add_account_item(
        self,
        parent_item: QTreeWidgetItem,
        account: dict,
        accounts_dict: dict,
        color: str,
    ) -> float:
        """Agrega una cuenta y sus hijos recursivamente."""
        item = QTreeWidgetItem(parent_item)

        code = account.get("account_code", "")
        name = account.get("account_name", "")
        is_detail = account.get("is_detail", False)

        item.setText(0, f"{code} - {name}")

        # Obtener saldo
        balance = self._get_account_balance(account)

        # Estilo según si es cuenta detalle o grupo
        if not is_detail:
            font = QFont()
            font.setBold(True)
            item.setFont(0, font)
            item.setForeground(0, QColor(color))
        else:
            item.setForeground(0, QColor("#475569"))

        # Agregar hijos recursivamente
        children = [a for a in accounts_dict.values() if a.get("parent_account") == code]
        subtotal = balance

        for child in sorted(children, key=lambda x: x["account_code"]):
            child_balance = self._add_account_item(item, child, accounts_dict, color)
            subtotal += child_balance

        # Mostrar saldo
        if subtotal != 0 or is_detail:
            item.setText(1, f"RD$ {subtotal:,.2f}")
            item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            if not is_detail:
                font = QFont()
                font.setBold(True)
                item.setFont(1, font)
                item.setForeground(1, QColor(color))

        return subtotal

    def _get_account_balance(self, account: dict) -> float:
        """Obtiene el saldo de una cuenta."""
        if not account.get("is_detail", False):
            return 0.0
        
        account_code = account.get("account_code", "")
        
        # ✅ DETECTAR TIPO POR CÓDIGO (FALLBACK)
        account_type = account.get("account_type", "")
        
        if not account_type:
            # Detectar por código
            first_digit = account_code[0] if account_code else ""
            if first_digit == "1":
                account_type = "ACTIVO"
            elif first_digit == "2":
                account_type = "PASIVO"
            elif first_digit == "3":
                account_type = "PATRIMONIO"
            elif first_digit == "4": 
                account_type = "INGRESO"
            elif first_digit == "5":
                account_type = "GASTO"
        
        try:
            if hasattr(self.controller, "get_account_balance"):
                print(f"[BALANCE] Obteniendo saldo de {account_code}")
                
                balance_data = self.controller.get_account_balance(
                    self.company_id,
                    account_code,
                    self.current_year_int,
                    int(self.current_month_str)
                )
                
                closing = float(balance_data.get("closing_balance", 0.0))
                
                # ✅ INVERSIÓN DE SIGNO PARA PATRIMONIO Y PASIVO
                if account_type in ("PASIVO", "PATRIMONIO"):
                    closing = -closing
                
                print(f"[BALANCE]   {account_code} = {closing:,.2f} (tipo: {account_type})")
                
                return closing
        except Exception as e:
            print(f"[BALANCE] ❌ Error obteniendo saldo de {account_code}: {e}")
            import traceback
            traceback.print_exc()
        
        return 0.0

    def _verify_balance(self, total_activos: float, total_pasivo_patrimonio: float):
        """Verifica que el balance cuadre."""
        difference = abs(total_activos - total_pasivo_patrimonio)

        if difference < 0.01:  # Tolerancia de 1 centavo
            self.verify_status.setText("✅ Balance Cuadrado")
            self.verify_status.setStyleSheet("font-size: 14px; font-weight: 700; color: #15803D;")
        else:
            self.verify_status.setText(f"⚠️ Descuadre: RD$ {difference:,.2f}")
            self.verify_status.setStyleSheet("font-size: 14px; font-weight: 700; color: #DC2626;")
