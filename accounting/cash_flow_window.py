from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QComboBox,
    QMessageBox,
    QScrollArea,
    QWidget,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QPalette


class CashFlowWindow(QDialog):
    """
    Estado de Flujo de Efectivo (Cash Flow Statement).
    """

    MONTHS_MAP = {
        "Todos": None,
        "Enero": "01", "Febrero": "02", "Marzo": "03", "Abril": "04",
        "Mayo": "05", "Junio": "06", "Julio": "07", "Agosto": "08",
        "Septiembre": "09", "Octubre": "10", "Noviembre": "11", "Diciembre": "12",
    }

    # Mapeo de cuentas a categorías de flujo
    ACCOUNT_CATEGORIES = {
        "4.1.": "operating", "5.1.": "operating", "5.2.": "operating",
        "1.1.2.": "operating", "2.1.1.": "operating",
        "1.2.1.": "investing",
        "3.1.": "financing", "2.2.": "financing",
    }

    def __init__(
        self,
        parent,
        controller,
        company_id,
        company_name: str,
        year: int | None = None,
    ):
        super().__init__(parent)
        self.controller = controller
        self.company_id = company_id
        self.company_name = company_name

        if not year:
            year = QDate.currentDate().year()
        self.current_year = year

        self.start_month = "01"
        self.end_month = "12"

        self.setWindowTitle(f"Flujo de Efectivo - {company_name}")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 900)

        from PyQt6.QtCore import Qt as QtCore
        self.setWindowFlags(
            QtCore.WindowType.Window |
            QtCore.WindowType.WindowMinMaxButtonsHint |
            QtCore.WindowType.WindowCloseButtonHint
        )

        self._build_ui()
        self._load_cash_flow()

    # =========================
    # UI ESTRUCTURA
    # =========================
    def _build_ui(self):
        # Layout principal de la ventana
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # 1. HEADER (Fijo en la parte superior, fuera del scroll)
        header_card = QFrame()
        header_card.setObjectName("headerCard")
        # Política fija para que no se estire
        header_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(18, 14, 18, 14)
        header_layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        title = QLabel("💵 Estado de Flujo de Efectivo")
        title.setObjectName("titleLabel")
        top_row.addWidget(title)
        top_row.addStretch()

        def mk_lbl(text: str):
            l = QLabel(text)
            l.setObjectName("fieldLabel")
            return l

        top_row.addWidget(mk_lbl("Desde:"))
        self.start_month_selector = QComboBox()
        self.start_month_selector.setObjectName("modernCombo")
        for m in self.MONTHS_MAP.keys():
            if m != "Todos":
                self.start_month_selector.addItem(m)
        self.start_month_selector.currentIndexChanged.connect(self._on_period_changed)
        top_row.addWidget(self.start_month_selector)

        top_row.addWidget(mk_lbl("Hasta:"))
        self.end_month_selector = QComboBox()
        self.end_month_selector.setObjectName("modernCombo")
        for m in self.MONTHS_MAP.keys():
            if m != "Todos":
                self.end_month_selector.addItem(m)
        self.end_month_selector.setCurrentIndex(11)
        self.end_month_selector.currentIndexChanged.connect(self._on_period_changed)
        top_row.addWidget(self.end_month_selector)

        top_row.addWidget(mk_lbl("Año:"))
        self.year_selector = QComboBox()
        self.year_selector.setObjectName("modernCombo")
        self.year_selector.currentIndexChanged.connect(self._on_period_changed)
        top_row.addWidget(self.year_selector)

        self.btn_refresh = QPushButton("🔃  Refrescar")
        self.btn_refresh.setObjectName("refreshButton")
        self.btn_refresh.clicked.connect(self._load_cash_flow)
        self.btn_refresh.setMinimumWidth(130)
        self.btn_refresh.setFixedHeight(36)
        top_row.addWidget(self.btn_refresh)

        header_layout.addLayout(top_row)

        self.subtitle_label = QLabel(self.company_name)
        self.subtitle_label.setObjectName("subtitleLabel")
        header_layout.addWidget(self.subtitle_label)

        # Agregamos el Header al root (fijo)
        root.addWidget(header_card)

        # 2. SCROLL AREA (Para el contenido dinámico)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("cashScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Contenedor interno del scroll
        self.content_container = QWidget()
        self.content_container.setObjectName("cashContainer")
        
        # Layout para las tarjetas dinámicas
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(4, 4, 16, 4) # Margen derecho para scrollbar
        self.content_layout.setSpacing(20)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll.setWidget(self.content_container)
        root.addWidget(self.scroll)

        # ===== ESTILOS =====
        self.setStyleSheet("""
            QDialog { background-color: #F8F9FA; }

            QFrame#headerCard {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }

            QLabel#titleLabel { font-size: 20px; font-weight: 800; color: #0F172A; }
            QLabel#subtitleLabel { font-size: 13px; color: #64748B; }
            QLabel#fieldLabel { font-weight: 700; color: #475569; font-size: 13px; }

            /* Scroll Area Transparente */
            QScrollArea#cashScroll { background-color: transparent; border: none; }
            QWidget#cashContainer { background-color: transparent; }

            QComboBox#modernCombo {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 6px 10px;
                color: #0F172A;
                font-size: 13px;
                min-width: 110px;
            }
            QComboBox#modernCombo:hover { border-color: #3B82F6; }

            QPushButton#refreshButton {
                background-color: #64748B;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0px 14px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton#refreshButton:hover { background-color: #475569; }

            /* Cards */
            QFrame#cfSectionCard {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E2E8F0;
            }

            QFrame#cfSummaryCard {
                background-color: #F8FAFC;
                border-radius: 12px;
                border: 2px solid #3B82F6; /* Borde azul para el resumen */
            }

            /* Rows */
            QLabel#rowDesc { font-size: 13px; color: #334155; font-weight: 500; }
            QLabel#rowAmt  { font-size: 13px; font-weight: 700; }
            QLabel#totalLbl { font-size: 13px; font-weight: 800; color: #0F172A; text-transform: uppercase; }
            QLabel#totalAmt { font-size: 15px; font-weight: 900; }

            QFrame#divider { background-color: #E2E8F0; }

            QMessageBox { background-color: #FFFFFF; }
            QMessageBox QLabel { color: #0F172A; font-size: 13px; background-color: transparent; }
            QMessageBox QPushButton {
                background-color: #1E293B;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 6px 16px;
                min-width: 90px;
            }
            QMessageBox QPushButton:hover { background-color: #334155; }
        """)

        self._init_period_selectors()

    # =========================
    # Periodo
    # =========================
    def _init_period_selectors(self):
        self.year_selector.clear()
        base_year = self.current_year
        years = [base_year - 1, base_year, base_year + 1]
        for y in years:
            self.year_selector.addItem(str(y))
        self.year_selector.setCurrentIndex(1)
        self._update_subtitle()

    def _update_subtitle(self):
        start_month_name = self.start_month_selector.currentText()
        end_month_name = self.end_month_selector.currentText()
        year = self.year_selector.currentText()

        if start_month_name == "Enero" and end_month_name == "Diciembre":
            period = f"Año {year}"
        else:
            period = f"{start_month_name} - {end_month_name} {year}"

        self.subtitle_label.setText(f"{self.company_name} - {period}")

    def _on_period_changed(self):
        start_month_name = self.start_month_selector.currentText()
        end_month_name = self.end_month_selector.currentText()

        self.start_month = self.MONTHS_MAP.get(start_month_name, "01")
        self.end_month = self.MONTHS_MAP.get(end_month_name, "12")

        try:
            self.current_year = int(self.year_selector.currentText())
        except Exception:
            self.current_year = QDate.currentDate().year()

        self._update_subtitle()
        self._load_cash_flow()

    # =========================
    # Flujo de Efectivo
    # =========================
    def _load_cash_flow(self):
        # 1. LIMPIEZA SEGURA: Eliminamos todo del layout de contenido
        # Al usar .hide() antes de deleteLater(), evitamos "fantasmas" visuales
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().hide() 
                item.widget().deleteLater()

        try:
            cash_accounts = self._get_cash_accounts()
            if not cash_accounts:
                self._show_empty_state()
                return

            opening_balance = self._get_opening_balance(cash_accounts)
            closing_balance = self._get_closing_balance(cash_accounts)
            flows = self._classify_cash_flows()

            operating_items = flows.get("operating", [])
            investing_items = flows.get("investing", [])
            financing_items = flows.get("financing", [])

            # 2. Agregar Tarjetas
            self.content_layout.addWidget(self._build_section_card(
                "ACTIVIDADES DE OPERACIÓN", operating_items, accent="#15803D"
            ))
            self.content_layout.addWidget(self._build_section_card(
                "ACTIVIDADES DE INVERSIÓN", investing_items, accent="#EA580C"
            ))
            self.content_layout.addWidget(self._build_section_card(
                "ACTIVIDADES DE FINANCIAMIENTO", financing_items, accent="#2563EB"
            ))

            net_operating = sum(i.get("amount", 0.0) for i in operating_items)
            net_investing = sum(i.get("amount", 0.0) for i in investing_items)
            net_financing = sum(i.get("amount", 0.0) for i in financing_items)
            net_change = net_operating + net_investing + net_financing

            # 3. Tarjeta de Resumen (Borde Azul)
            self.content_layout.addWidget(self._build_summary_card(
                opening_balance, closing_balance, net_change,
                net_operating, net_investing, net_financing
            ))

            # 4. Stretch al final para empujar todo hacia arriba
            self.content_layout.addStretch()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando flujo de efectivo:\n{e}")
            import traceback
            traceback.print_exc()

    def _show_empty_state(self):
        no_data = QLabel(
            "No se encontraron cuentas de efectivo.\n\n"
            "Asegúrate de tener cuentas con código 1.1.1.* en tu plan de cuentas."
        )
        no_data.setStyleSheet(
            "font-size: 14px; color: #64748B; padding: 40px; "
            "background-color: #FFFFFF; border-radius: 12px; "
            "border: 2px dashed #CBD5E1;"
        )
        no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(no_data)
        self.content_layout.addStretch()

    # =========================
    # Data helpers
    # =========================
    def _get_cash_accounts(self) -> list:
        if not hasattr(self.controller, "get_chart_of_accounts"):
            return []
        accounts = self.controller.get_chart_of_accounts(self.company_id) or []
        return [
            a for a in accounts
            if a.get("account_code", "").startswith("1.1.1.") and a.get("is_detail", False)
        ]

    def _get_opening_balance(self, cash_accounts: list) -> float:
        total = 0.0
        for acc in cash_accounts:
            bal = self._get_account_balance(acc.get("account_code"), int(self.start_month))
            total += float(bal.get("opening_balance", 0.0))
        return total

    def _get_closing_balance(self, cash_accounts: list) -> float:
        total = 0.0
        for acc in cash_accounts:
            bal = self._get_account_balance(acc.get("account_code"), int(self.end_month))
            total += float(bal.get("closing_balance", 0.0))
        return total

    def _get_account_balance(self, account_code: str, month: int) -> dict:
        if not hasattr(self.controller, "get_account_balance"):
            return {}
        try:
            return self.controller.get_account_balance(self.company_id, account_code, self.current_year, month) or {}
        except Exception:
            return {}

    def _classify_cash_flows(self) -> dict:
        flows = {"operating": [], "investing": [], "financing": []}
        if not hasattr(self.controller, "get_journal_entries"):
            return flows

        try:
            entries = self.controller.get_journal_entries(
                self.company_id,
                year=self.current_year,
                month=None,
                limit=1000
            ) or []

            start_m = int(self.start_month)
            end_m = int(self.end_month)

            for entry in entries:
                entry_month = entry.get("month")
                if not entry_month:
                    continue
                if not (start_m <= entry_month <= end_m):
                    continue

                lines = entry.get("lines", [])
                for line in lines:
                    cash_acc = line.get("account_id", "")
                    if not cash_acc.startswith("1.1.1."):
                        continue

                    debit = float(line.get("debit", 0.0))
                    credit = float(line.get("credit", 0.0))
                    net_amount = debit - credit
                    if net_amount == 0:
                        continue

                    category = "operating"
                    for other in lines:
                        if other is line:
                            continue
                        other_acc = other.get("account_id", "")
                        category = self._categorize_account(other_acc)
                        break

                    flows[category].append({
                        "description": line.get("description", entry.get("description", "")) or "Otros movimientos",
                        "amount": net_amount,
                        "reference": entry.get("entry_id", ""),
                        "date": entry.get("entry_date"),
                    })

        except Exception as e:
            print(f"[CASH_FLOW] Error clasificando flujos: {e}")

        return flows

    def _categorize_account(self, account_code: str) -> str:
        for prefix, cat in self.ACCOUNT_CATEGORIES.items():
            if account_code.startswith(prefix):
                return cat
        return "operating"

    # =========================
    # UI builders
    # =========================
    def _build_section_card(self, title: str, items: list, accent: str) -> QFrame:
        card = QFrame()
        card.setObjectName("cfSectionCard")
        # Minimum para que crezca lo necesario
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # Header de la tarjeta
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        bar = QFrame()
        bar.setFixedWidth(4)
        bar.setFixedHeight(18)
        bar.setStyleSheet(f"background-color: {accent}; border-radius: 2px;")
        header_row.addWidget(bar)

        t = QLabel(title)
        t.setStyleSheet(f"font-size: 13px; font-weight: 900; color: {accent}; letter-spacing: 0.5px;")
        header_row.addWidget(t)
        header_row.addStretch()

        layout.addLayout(header_row)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        layout.addWidget(div)

        # Agrupación de datos
        grouped: dict[str, float] = {}
        for it in items:
            desc = (it.get("description") or "Otros movimientos").strip()
            grouped[desc] = grouped.get(desc, 0.0) + float(it.get("amount", 0.0))

        total = 0.0

        if not grouped:
            empty = QLabel("Sin movimientos en este periodo")
            empty.setStyleSheet("color: #94A3B8; font-style: italic; padding: 8px 0px;")
            layout.addWidget(empty)
        else:
            for desc in sorted(grouped.keys()):
                amt = grouped[desc]

                roww = QWidget()
                row = QHBoxLayout(roww)
                row.setContentsMargins(0, 2, 0, 2)
                row.setSpacing(12)

                d = QLabel(desc)
                d.setObjectName("rowDesc")
                d.setWordWrap(True) # Importante para evitar textos muy anchos
                d.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
                row.addWidget(d, 1)

                a = QLabel(self._fmt_amount(amt))
                a.setObjectName("rowAmt")
                a.setFixedWidth(160)
                a.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                a.setStyleSheet(f"color: {'#15803D' if amt >= 0 else '#DC2626'};")
                row.addWidget(a)

                layout.addWidget(roww)
                total += amt

        div2 = QFrame()
        div2.setObjectName("divider")
        div2.setFixedHeight(1)
        layout.addWidget(div2)

        # Total footer
        totalw = QWidget()
        totalrow = QHBoxLayout(totalw)
        totalrow.setContentsMargins(0, 0, 0, 0)
        totalrow.setSpacing(12)

        tl = QLabel("Efectivo neto de esta actividad:")
        tl.setObjectName("totalLbl")
        totalrow.addWidget(tl, 1)

        ta = QLabel(f"RD$ {total:,.2f}")
        ta.setObjectName("totalAmt")
        ta.setFixedWidth(160)
        ta.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        ta.setStyleSheet(f"color: {accent};")
        totalrow.addWidget(ta)

        layout.addWidget(totalw)

        return card

    def _build_summary_card(
        self,
        opening: float,
        closing: float,
        net_change: float,
        net_operating: float,
        net_investing: float,
        net_financing: float,
    ) -> QFrame:
        if closing == 0 and opening == 0:
            closing = net_change
        elif closing == 0:
            closing = opening + net_change

        card = QFrame()
        card.setObjectName("cfSummaryCard")
        # IMPORTANTE: Minimum para evitar solapamiento
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        title = QLabel("📊  RESUMEN DEL FLUJO DE EFECTIVO")
        title.setStyleSheet("font-size: 14px; font-weight: 900; color: #0F172A; letter-spacing: 0.6px;")
        layout.addWidget(title)

        layout.addWidget(self._summary_row("Actividades de Operación", net_operating, "#15803D"))
        layout.addWidget(self._summary_row("Actividades de Inversión", net_investing, "#EA580C"))
        layout.addWidget(self._summary_row("Actividades de Financiamiento", net_financing, "#2563EB"))

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        layout.addWidget(div)

        layout.addWidget(self._summary_row("AUMENTO NETO EN EFECTIVO", net_change, "#1E40AF", big=True))
        layout.addWidget(self._summary_row("Efectivo al inicio del periodo", opening, "#475569"))

        div2 = QFrame()
        div2.setObjectName("divider")
        div2.setFixedHeight(1)
        layout.addWidget(div2)

        # Final Highlight
        roww = QWidget()
        row = QHBoxLayout(roww)
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(12)

        l = QLabel("EFECTIVO AL FINAL DEL PERIODO")
        l.setStyleSheet("font-size: 14px; font-weight: 900; color: #0F172A;")
        row.addWidget(l, 1)

        v = QLabel(f"RD$ {closing:,.2f}")
        v.setFixedWidth(220)
        v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        v.setStyleSheet("font-size: 18px; font-weight: 900; color: #15803D;")
        row.addWidget(v)

        layout.addWidget(roww)
        return card

    def _summary_row(self, label: str, value: float, color: str, big: bool = False) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(12)

        l = QLabel(label)
        l.setStyleSheet(f"font-size: {14 if big else 13}px; font-weight: {900 if big else 600}; color: #334155;")
        row.addWidget(l, 1)

        v = QLabel(f"RD$ {value:,.2f}")
        v.setFixedWidth(220)
        v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        v.setStyleSheet(f"font-size: {16 if big else 13}px; font-weight: {900 if big else 800}; color: {color};")
        row.addWidget(v)

        return w

    @staticmethod
    def _fmt_amount(amount: float) -> str:
        if amount < 0:
            return f"(RD$ {abs(amount):,.2f})"
        return f"RD$ {amount:,.2f}"