from __future__ import annotations

import datetime
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QComboBox,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QSizePolicy,  # ✅ FIX botones
)
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette


class GeneralLedgerWindow(QDialog):
    """
    Libro Mayor (General Ledger).

    Muestra todos los movimientos de una cuenta específica en un periodo:
    - Saldo inicial
    - Asientos débito
    - Asientos crédito
    - Saldo final (acumulado)
    """

    MONTHS_MAP = {
        "Todos": None,
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
    ):
        super().__init__(parent)
        self.controller = controller
        self.company_id = company_id
        self.company_name = company_name

        # Periodo actual
        today = QDate.currentDate()
        self.current_month_str = f"{today.month():02d}"
        self.current_year_int = today.year()

        # Cuenta seleccionada
        self.selected_account = None
        self.accounts_dict = {}  # {account_code: account_data}

        self.setWindowTitle(f"Libro Mayor - {company_name}")
        self.resize(1100, 700)
        self.setModal(True)

        self._build_ui()
        self._load_accounts()

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
        header_layout.setSpacing(12)

        title_row = QHBoxLayout()
        title_row.setSpacing(12)

        title = QLabel("📖 Libro Mayor")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A;")
        title_row.addWidget(title)
        title_row.addStretch()

        # Periodo
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

        header_layout.addLayout(title_row)

        # Subtítulo
        self.subtitle_label = QLabel(f"{self.company_name}")
        self.subtitle_label.setStyleSheet("font-size: 12px; color: #64748B;")
        header_layout.addWidget(self.subtitle_label)

        root.addWidget(header_card)

        # === SELECTOR DE CUENTA ===
        account_card = QFrame()
        account_card.setObjectName("accountCard")
        account_layout = QVBoxLayout(account_card)
        account_layout.setContentsMargins(20, 16, 20, 16)
        account_layout.setSpacing(12)

        account_title = QLabel("Seleccionar Cuenta:")
        account_title.setStyleSheet("font-weight: 700; color: #1E293B; font-size: 14px;")
        account_layout.addWidget(account_title)

        search_row = QHBoxLayout()
        search_row.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("modernInput")
        self.search_input.setPlaceholderText("Buscar por código o nombre de cuenta...")
        self.search_input.textChanged.connect(self._filter_accounts)
        search_row.addWidget(self.search_input, 3)

        self.account_combo = QComboBox()
        self.account_combo.setObjectName("modernCombo")
        self.account_combo.currentIndexChanged.connect(self._on_account_selected)
        search_row.addWidget(self.account_combo, 2)

        self.btn_load = QPushButton("🔍 Ver Movimientos")
        self.btn_load.setObjectName("primaryButton")
        self.btn_load.clicked.connect(self._load_ledger)

        # ✅ FIX: evitar que el botón se “pierda” o quede mini
        self.btn_load.setMinimumWidth(170)
        self.btn_load.setFixedHeight(34)
        self.btn_load.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        search_row.addWidget(self.btn_load)

        account_layout.addLayout(search_row)
        root.addWidget(account_card)

        # === RESUMEN DE CUENTA ===
        summary_card = QFrame()
        summary_card.setObjectName("summaryCard")
        summary_layout = QHBoxLayout(summary_card)
        summary_layout.setContentsMargins(20, 16, 20, 16)
        summary_layout.setSpacing(20)

        self.lbl_opening = self._create_summary_label("Saldo Inicial:", "RD$ 0.00", "#64748B")
        self.lbl_debits = self._create_summary_label("Total Débitos:", "RD$ 0.00", "#15803D")
        self.lbl_credits = self._create_summary_label("Total Créditos:", "RD$ 0.00", "#DC2626")
        self.lbl_closing = self._create_summary_label("Saldo Final:", "RD$ 0.00", "#1E40AF")

        summary_layout.addWidget(self.lbl_opening["widget"])
        summary_layout.addWidget(self.lbl_debits["widget"])
        summary_layout.addWidget(self.lbl_credits["widget"])
        summary_layout.addWidget(self.lbl_closing["widget"])

        root.addWidget(summary_card)

        # === TABLA DE MOVIMIENTOS ===
        self.table = QTableWidget()
        self.table.setObjectName("ledgerTable")
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Fecha", "Referencia", "Descripción", "Débito", "Crédito", "Saldo"]
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)

        # Forzar palette claro
        pal = self.table.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#F9FAFB"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#0F172A"))
        self.table.setPalette(pal)

        root.addWidget(self.table)

        # === ESTILOS ===
        # ✅ Fixes:
        # - QFrame.summaryItem (antes tenía "QFrame.  summaryItem" incorrecto)
        # - Botón primaryButton con height fijo para que no se colapse
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }

            QFrame#headerCard, QFrame#accountCard {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }

            QFrame#summaryCard {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 2px solid #3B82F6;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #EFF6FF,
                    stop:1 #FFFFFF
                );
            }

            /* ✅ FIX: selector correcto para property class="summaryItem" */
            QFrame[class="summaryItem"] {
                background-color: transparent;
                border-radius: 8px;
                padding: 8px;
            }

            QLineEdit#modernInput {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px 12px;
                color: #0F172A;
                font-size: 13px;
            }
            QLineEdit#modernInput:focus { border-color: #3B82F6; border-width: 2px; }

            QComboBox#modernCombo {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 12px;
                color: #0F172A;
                font-size: 13px;
                min-width: 200px;
            }
            QComboBox#modernCombo:hover { border-color: #3B82F6; }

            QPushButton#primaryButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;

                /* ✅ FIX: evitar botón mini */
                min-width: 170px;
                height: 34px;
                padding: 0px 18px;

                font-weight: 600;
                font-size: 14px;
            }
            QPushButton#primaryButton:hover { background-color: #2563EB; }

            QTableWidget#ledgerTable {
                background-color: #FFFFFF;
                alternate-background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                gridline-color: #E5E7EB;
                color: #0F172A;
                font-size: 13px;
            }

            QTableWidget#ledgerTable::item {
                padding: 8px;
                color: #0F172A;
            }

            QTableWidget#ledgerTable::item:alternate {
                background-color: #F9FAFB;
            }

            QTableWidget#ledgerTable::item:selected {
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

            /* QMessageBox (para que no salga oscuro con tema global) */
            QMessageBox { background-color: #FFFFFF; }
            QMessageBox QLabel { color: #0F172A; font-size: 13px; background-color: transparent; }
            QMessageBox QPushButton {
                background-color: #1E293B;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 6px 16px;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover { background-color: #334155; }
        """)

        # Inicializar selectores
        self._init_period_selectors()

        # ✅ Extra: forzar que el warning no quede “apagado” si el global theme lo afecta
        QTimer.singleShot(0, self._force_msgbox_palette)

    def _force_msgbox_palette(self):
        """Pequeño empujón al palette global del dialog (no rompe temas, pero evita textos grises en msgbox)."""
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#F8F9FA"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#0F172A"))
        self.setPalette(pal)

    def _create_summary_label(self, title: str, value: str, color: str):
        """Crea un label de resumen."""
        widget = QFrame()
        widget.setProperty("class", "summaryItem")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600;")
        layout.addWidget(title_lbl)

        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: 700;")
        layout.addWidget(value_lbl)

        return {"widget": widget, "title": title_lbl, "value": value_lbl}

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

        if month_name == "Todos":
            period = f"Año {year}"
        else:
            period = f"{month_name} {year}"

        self.subtitle_label.setText(f"{self.company_name} - {period}")

    def _on_period_changed(self):
        """Maneja cambio de periodo."""
        month_name = self.month_selector.currentText()
        self.current_month_str = self.MONTHS_MAP.get(month_name)

        try:
            self.current_year_int = int(self.year_selector.currentText())
        except Exception:
            self.current_year_int = QDate.currentDate().year()

        self._update_subtitle()

        if self.selected_account:
            self._load_ledger()

    # =========================
    # Cuentas
    # =========================
    def _load_accounts(self):
        """Carga todas las cuentas de detalle."""
        try:
            if not hasattr(self.controller, "get_chart_of_accounts"):
                QMessageBox.critical(self, "Error", "Método get_chart_of_accounts no implementado.")
                return

            accounts = self.controller.get_chart_of_accounts(self.company_id) or []
            detail_accounts = [a for a in accounts if a.get("is_detail", False)]

            self.accounts_dict = {a["account_code"]: a for a in detail_accounts}

            self.account_combo.clear()
            self.account_combo.addItem("-- Seleccionar cuenta --", None)

            for acc in sorted(detail_accounts, key=lambda x: x.get("account_code", "")):
                code = acc.get("account_code", "")
                name = acc.get("account_name", "")
                display = f"{code} - {name}"
                self.account_combo.addItem(display, code)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando cuentas:\n{e}")
            import traceback
            traceback.print_exc()

    def _filter_accounts(self, text: str):
        """Filtra cuentas en el combo según el texto de búsqueda."""
        search = text.lower().strip()

        self.account_combo.clear()
        self.account_combo.addItem("-- Seleccionar cuenta --", None)

        for code, acc in sorted(self.accounts_dict.items()):
            name = acc.get("account_name", "")
            display = f"{code} - {name}"

            if not search or search in code.lower() or search in name.lower():
                self.account_combo.addItem(display, code)

    def _on_account_selected(self):
        """Maneja selección de cuenta."""
        account_code = self.account_combo.currentData()
        if account_code:
            self.selected_account = self.accounts_dict.get(account_code)
        else:
            self.selected_account = None

    # =========================
    # Libro Mayor
    # =========================
    def _load_ledger(self):
        """Carga los movimientos de la cuenta seleccionada."""
        if not self.selected_account:
            QMessageBox.warning(self, "Cuenta Requerida", "Seleccione una cuenta primero.")
            return

        account_code = self.selected_account.get("account_code")

        try:
            balance_data = {}
            if hasattr(self.controller, "get_account_balance"):
                balance_data = self.controller.get_account_balance(
                    self.company_id,
                    account_code,
                    self.current_year_int,
                    int(self.current_month_str) if self.current_month_str else 1
                ) or {}

            opening_balance = float(balance_data.get("opening_balance", 0.0))
            total_debit = float(balance_data.get("total_debit", 0.0))
            total_credit = float(balance_data.get("total_credit", 0.0))
            closing_balance = float(balance_data.get("closing_balance", 0.0))

            self.lbl_opening["value"].setText(f"RD$ {opening_balance:,.2f}")
            self.lbl_debits["value"].setText(f"RD$ {total_debit:,.2f}")
            self.lbl_credits["value"].setText(f"RD$ {total_credit:,.2f}")
            self.lbl_closing["value"].setText(f"RD$ {closing_balance:,.2f}")

            entries = []
            if hasattr(self.controller, "get_journal_entries"):
                entries = self.controller.get_journal_entries(
                    self.company_id,
                    year=self.current_year_int,
                    month=int(self.current_month_str) if self.current_month_str else None,
                    limit=500
                ) or []

            movements = []
            for entry in entries:
                entry_date = entry.get("entry_date")
                entry_id = entry.get("entry_id", "")
                lines = entry.get("lines", [])

                for line in lines:
                    if line.get("account_id") == account_code:
                        movements.append({
                            "date": entry_date,
                            "reference": entry_id,
                            "description": line.get("description", entry.get("description", "")),
                            "debit": float(line.get("debit", 0.0)),
                            "credit": float(line.get("credit", 0.0)),
                        })

            movements.sort(key=lambda x: x["date"] if x["date"] else datetime.datetime(1970, 1, 1))
            self._populate_table(opening_balance, movements)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando libro mayor:\n{e}")
            import traceback
            traceback.print_exc()

    def _populate_table(self, opening_balance: float, movements: list):
        """Puebla la tabla con los movimientos."""
        self.table.setRowCount(0)
        running_balance = opening_balance

        row = self.table.rowCount()
        self.table.insertRow(row)

        month_name = self.month_selector.currentText()
        year = self.year_selector.currentText()

        if month_name == "Todos":
            date_str = f"01/01/{year}"
        else:
            date_str = f"01/{self.current_month_str}/{year}"

        self.table.setItem(row, 0, QTableWidgetItem(date_str))

        item_ref = QTableWidgetItem("SALDO INICIAL")
        item_ref.setForeground(QColor("#64748B"))
        font = QFont()
        font.setBold(True)
        item_ref.setFont(font)
        self.table.setItem(row, 1, item_ref)

        self.table.setItem(row, 2, QTableWidgetItem(""))
        self.table.setItem(row, 3, QTableWidgetItem(""))
        self.table.setItem(row, 4, QTableWidgetItem(""))

        balance_item = QTableWidgetItem(f"RD$ {running_balance:,.2f}")
        balance_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        balance_item.setFont(font)
        self.table.setItem(row, 5, balance_item)

        for mov in movements:
            row = self.table.rowCount()
            self.table.insertRow(row)

            date_val = mov["date"]
            if isinstance(date_val, datetime.datetime):
                date_str = date_val.strftime("%d/%m/%Y")
            elif isinstance(date_val, datetime.date):
                date_str = date_val.strftime("%d/%m/%Y")
            else:
                date_str = str(date_val)[:10]

            self.table.setItem(row, 0, QTableWidgetItem(date_str))
            self.table.setItem(row, 1, QTableWidgetItem(mov["reference"]))
            self.table.setItem(row, 2, QTableWidgetItem(mov["description"]))

            debit = mov["debit"]
            debit_item = QTableWidgetItem(f"RD$ {debit:,.2f}" if debit > 0 else "")
            debit_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if debit > 0:
                debit_item.setForeground(QColor("#15803D"))
            self.table.setItem(row, 3, debit_item)

            credit = mov["credit"]
            credit_item = QTableWidgetItem(f"RD$ {credit:,.2f}" if credit > 0 else "")
            credit_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if credit > 0:
                credit_item.setForeground(QColor("#DC2626"))
            self.table.setItem(row, 4, credit_item)

            running_balance += debit - credit
            balance_item = QTableWidgetItem(f"RD$ {running_balance:,.2f}")
            balance_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            balance_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.table.setItem(row, 5, balance_item)
