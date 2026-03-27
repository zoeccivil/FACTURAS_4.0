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
    QScrollArea,
    QWidget,
    QSizePolicy,
    QGridLayout,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QPalette


class JournalDiaryWindow(QDialog):
    """
    Libro Diario (Journal Diary).

    Muestra todos los asientos contables en orden cronológico
    con detalle completo de cada partida.
    """

    MONTHS_MAP = {
        "Todos": None,
        "Enero": "01", "Febrero": "02", "Marzo": "03", "Abril": "04",
        "Mayo": "05", "Junio": "06", "Julio":  "07", "Agosto": "08",
        "Septiembre": "09", "Octubre":  "10", "Noviembre":  "11", "Diciembre":  "12",
    }

    def __init__(
        self,
        parent,
        controller,
        company_id,
        company_name:  str,
    ):
        super().__init__(parent)
        self.controller = controller
        self.company_id = company_id
        self.company_name = company_name

        # Periodo actual
        today = QDate.currentDate()
        self.current_month_str = f"{today.month():02d}"
        self.current_year_int = today.year()

        self.setWindowTitle(f"Libro Diario - {company_name}")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 850)

        # Habilitar Maximizar/Minimizar
        from PyQt6.QtCore import Qt as QtCore
        self.setWindowFlags(
            QtCore.WindowType.Window |
            QtCore.WindowType.WindowMinMaxButtonsHint |
            QtCore.WindowType.WindowCloseButtonHint
        )

        self._build_ui()
        self._load_diary()

    # =========================
    # UI CONSTRUCTION
    # =========================
    def _build_ui(self):
        # Root layout sin márgenes para maximizar espacio del scroll
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 1. HEADER (Fijo arriba)
        header_card = QFrame()
        header_card.setObjectName("headerCard")
        header_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        icon_lbl = QLabel("📓")
        icon_lbl.setStyleSheet("font-size: 22px;")
        top_row.addWidget(icon_lbl)

        title = QLabel("Libro Diario")
        title.setObjectName("titleLabel")
        top_row.addWidget(title)
        top_row.addStretch()

        def mk_lbl(t):
            l = QLabel(t)
            l.setObjectName("fieldLabel")
            return l

        # Filtros
        top_row.addWidget(mk_lbl("Mes:"))
        self.month_selector = QComboBox()
        self.month_selector.setObjectName("modernCombo")
        for month in self.MONTHS_MAP.keys():
            self.month_selector.addItem(month)
        self.month_selector.currentIndexChanged.connect(self._on_period_changed)
        top_row.addWidget(self.month_selector)

        top_row.addWidget(mk_lbl("Año:"))
        self.year_selector = QComboBox()
        self.year_selector.setObjectName("modernCombo")
        self.year_selector.currentIndexChanged.connect(self._on_period_changed)
        top_row.addWidget(self.year_selector)

        self.btn_refresh = QPushButton("🔃  Refrescar")
        self.btn_refresh.setObjectName("refreshButton")
        self.btn_refresh.clicked.connect(self._load_diary)
        self.btn_refresh.setFixedWidth(120)
        top_row.addWidget(self.btn_refresh)

        header_layout.addLayout(top_row)

        self.subtitle_label = QLabel(f"{self.company_name}")
        self.subtitle_label.setObjectName("subtitleLabel")
        header_layout.addWidget(self.subtitle_label)

        root.addWidget(header_card)

        # 2. SCROLL AREA (Contenido dinámico)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("mainScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.entries_container = QWidget()
        self.entries_container.setObjectName("entriesContainer")
        self.entries_layout = QVBoxLayout(self.entries_container)
        self.entries_layout.setContentsMargins(24, 20, 24, 20)
        self.entries_layout.setSpacing(20) # Espacio entre asientos
        self.entries_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll.setWidget(self.entries_container)
        root.addWidget(self.scroll)

        # 3. FOOTER (Totales Globales - Fijo abajo)
        footer_card = QFrame()
        footer_card.setObjectName("footerCard")
        footer_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        footer_layout = QHBoxLayout(footer_card)
        footer_layout.setContentsMargins(24, 16, 24, 16)
        footer_layout.setSpacing(24)

        ft_lbl = QLabel("TOTALES DEL PERIODO:")
        ft_lbl.setObjectName("footerTitle")
        footer_layout.addWidget(ft_lbl)

        self.lbl_total_entries = QLabel("0 asientos")
        self.lbl_total_entries.setStyleSheet("color: #64748B; font-weight: 500; font-size: 13px;")
        footer_layout.addWidget(self.lbl_total_entries)

        footer_layout.addStretch()

        self.lbl_total_debits = QLabel("Débitos: RD$ 0.00")
        self.lbl_total_debits.setObjectName("footerDebit")
        footer_layout.addWidget(self.lbl_total_debits)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("color: #CBD5E1;")
        footer_layout.addWidget(line)

        self.lbl_total_credits = QLabel("Créditos: RD$ 0.00")
        self.lbl_total_credits.setObjectName("footerCredit")
        footer_layout.addWidget(self.lbl_total_credits)

        root.addWidget(footer_card)

        # ===== STYLES =====
        self.setStyleSheet("""
            QDialog { background-color: #F8F9FA; }

            QFrame#headerCard {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E2E8F0;
            }
            QFrame#footerCard {
                background-color: #FFFFFF;
                border-top: 1px solid #E2E8F0;
                border-bottom: 4px solid #3B82F6; /* Acento azul */
            }

            /* Scroll */
            QScrollArea#mainScroll { background-color: transparent; border: none; }
            QWidget#entriesContainer { background-color: transparent; }

            /* Textos */
            QLabel#titleLabel { font-size: 20px; font-weight: 800; color: #0F172A; }
            QLabel#subtitleLabel { font-size: 13px; color: #64748B; margin-left: 38px; }
            QLabel#fieldLabel { font-weight: 600; color: #475569; font-size: 13px; }

            QLabel#footerTitle { font-size: 14px; font-weight: 800; color: #0F172A; text-transform: uppercase; }
            QLabel#footerDebit { font-size: 15px; font-weight: 700; color: #15803D; }
            QLabel#footerCredit { font-size: 15px; font-weight: 700; color: #DC2626; }

            /* Inputs */
            QComboBox#modernCombo {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 5px 10px;
                color: #0F172A;
                min-width: 120px;
            }
            QComboBox#modernCombo:hover { border-color: #3B82F6; }

            QPushButton#refreshButton {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                color: #0F172A;
                font-weight: 600;
                padding: 6px 12px;
            }
            QPushButton#refreshButton:hover { background-color: #F1F5F9; border-color: #94A3B8; }

            /* Tarjetas de Asientos */
            QFrame#entryCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            QFrame#entryCardHeader {
                background-color: #F8FAFC;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom: 1px solid #F1F5F9;
            }

            /* Tabla interna simulada */
            QLabel#colHeader {
                color: #64748B; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
            }
            QLabel#cellText { color: #334155; font-size: 13px; }
            QLabel#cellAccount { color: #0F172A; font-weight: 600; font-size: 13px; }
            QLabel#cellAmount { font-family: 'Segoe UI', sans-serif; font-weight: 600; font-size: 13px; }
            
            QFrame#rowDivider { background-color: #F1F5F9; max-height: 1px; }
            
            QFrame#totalRowBg {
                background-color: #F8FAFC;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }

            /* Badge */
            QLabel#statusBadge {
                background-color: #DCFCE7; 
                color: #166534;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 700;
            }

            /* QMessageBox */
            QMessageBox { background-color: #FFFFFF; }
            QMessageBox QLabel { color: #0F172A; }
            QMessageBox QPushButton {
                background-color: #1E293B; color: #FFFFFF;
                border-radius: 6px; padding: 6px 16px; min-width: 80px;
            }
        """)

        # Inicializar selectores
        self._init_period_selectors()

    # =========================
    # LOGIC & DATA
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
            self.month_selector.setCurrentText(month_name)

        # Año
        self.year_selector.clear()
        base_year = self.current_year_int
        years = [base_year - 1, base_year, base_year + 1]
        for y in years:
            self.year_selector.addItem(str(y))
        
        self.year_selector.setCurrentText(str(base_year))

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
        self._load_diary()

    def _load_diary(self):
        """Carga todos los asientos del periodo."""
        # Limpiar contenedor de forma segura (evita fantasmas)
        while self.entries_layout.count():
            child = self.entries_layout.takeAt(0)
            if child.widget():
                child.widget().hide()
                child.widget().deleteLater()

        try:
            # Obtener asientos
            entries = []
            if hasattr(self.controller, "get_journal_entries"):
                m_int = int(self.current_month_str) if self.current_month_str else None
                
                entries = self.controller.get_journal_entries(
                    self.company_id,
                    year=self.current_year_int,
                    month=m_int,
                    limit=1000
                ) or []

            if not entries:
                self._show_empty_state()
                self._update_footer(0, 0, 0)
                return

            # Ordenar por fecha
            entries.sort(
                key=lambda x: x.get("entry_date") if x.get("entry_date") else datetime.datetime(1970, 1, 1),
                reverse=True # Más recientes arriba
            )

            # Totales acumulados
            total_debits = 0.0
            total_credits = 0.0

            # Crear card por cada asiento
            for entry in entries:
                card = self._create_entry_card(entry)
                self.entries_layout.addWidget(card)

                # Acumular totales
                total_debits += float(entry.get("total_debit", 0.0))
                total_credits += float(entry.get("total_credit", 0.0))

            # Push up
            self.entries_layout.addStretch()

            # Actualizar footer
            self._update_footer(len(entries), total_debits, total_credits)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando libro diario:\n{e}")
            import traceback
            traceback.print_exc()

    def _show_empty_state(self):
        lbl = QLabel("No hay asientos registrados en este periodo.")
        lbl.setStyleSheet("color: #94A3B8; font-size: 14px; font-style: italic; margin-top: 40px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.entries_layout.addWidget(lbl)
        self.entries_layout.addStretch()

    def _update_footer(self, count, debits, credits):
        self.lbl_total_entries.setText(f"{count} asiento{'s' if count != 1 else ''}")
        self.lbl_total_debits.setText(f"Débitos: RD$ {debits:,.2f}")
        self.lbl_total_credits.setText(f"Créditos: RD$ {credits:,.2f}")

    # =========================
    # CARD BUILDER
    # =========================
    def _create_entry_card(self, entry:  dict) -> QFrame:
        """Crea una card para un asiento contable."""
        card = QFrame()
        card.setObjectName("entryCard")
        # Minimum para crecer verticalmente lo necesario
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- A. HEADER DEL ASIENTO ---
        header = QFrame()
        header.setObjectName("entryCardHeader")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 10, 16, 10)
        h_layout.setSpacing(12)

        # Fecha
        entry_date = entry.get("entry_date")
        if isinstance(entry_date, datetime.datetime) or isinstance(entry_date, datetime.date):
            date_str = entry_date.strftime("%d/%m/%Y")
        else:
            date_str = str(entry_date)[:10]

        lbl_date = QLabel(f"📅  {date_str}")
        lbl_date.setStyleSheet("font-weight: 700; color: #0F172A; font-size: 13px;")
        h_layout.addWidget(lbl_date)

        # ID
        entry_id = entry.get("entry_id", "")
        lbl_id = QLabel(f"Asiento: {entry_id}")
        lbl_id.setStyleSheet("color: #2563EB; font-weight: 600; font-size: 13px;")
        h_layout.addWidget(lbl_id)

        h_layout.addStretch()

        # Status Badge
        status_lbl = QLabel("✓ Contabilizado")
        status_lbl.setObjectName("statusBadge")
        h_layout.addWidget(status_lbl)

        layout.addWidget(header)

        # --- B. CUERPO (Grid de líneas) ---
        body = QWidget()
        b_layout = QVBoxLayout(body)
        b_layout.setContentsMargins(16, 12, 16, 12)
        b_layout.setSpacing(10)

        # Referencia / Descripcion principal
        ref_text = entry.get("description") or entry.get("reference") or "Sin descripción"
        lbl_ref = QLabel(f"Referencia: {ref_text}")
        lbl_ref.setStyleSheet("color: #64748B; font-size: 12px;")
        b_layout.addWidget(lbl_ref)

        # Grid
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(0, 8, 0, 0)

        # Headers
        grid.addWidget(self._mk_header("CUENTA"), 0, 0)
        grid.addWidget(self._mk_header("DESCRIPCIÓN"), 0, 1)
        grid.addWidget(self._mk_header("DÉBITO", right=True), 0, 2)
        grid.addWidget(self._mk_header("CRÉDITO", right=True), 0, 3)

        # Filas
        row_idx = 1
        lines = entry.get("lines", [])
        
        for line in lines:
            if row_idx > 1:
                sep = QFrame()
                sep.setObjectName("rowDivider")
                sep.setFixedHeight(1)
                grid.addWidget(sep, row_idx, 0, 1, 4)
                row_idx += 1

            # Cuenta
            acode = line.get("account_id", "")
            aname = line.get("account_name", "")
            lbl_acc = QLabel(f"{acode}\n{aname}")
            lbl_acc.setObjectName("cellAccount")
            grid.addWidget(lbl_acc, row_idx, 0)

            # Desc
            lbl_desc = QLabel(line.get("description", ""))
            lbl_desc.setObjectName("cellText")
            lbl_desc.setWordWrap(True)
            grid.addWidget(lbl_desc, row_idx, 1)

            # Montos
            d = float(line.get("debit", 0))
            c = float(line.get("credit", 0))

            lbl_d = QLabel(f"RD$ {d:,.2f}" if d > 0 else "")
            lbl_d.setObjectName("cellAmount")
            lbl_d.setStyleSheet("color: #15803D;")
            lbl_d.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl_d.setFixedWidth(110)
            grid.addWidget(lbl_d, row_idx, 2)

            lbl_c = QLabel(f"RD$ {c:,.2f}" if c > 0 else "")
            lbl_c.setObjectName("cellAmount")
            lbl_c.setStyleSheet("color: #DC2626;")
            lbl_c.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl_c.setFixedWidth(110)
            grid.addWidget(lbl_c, row_idx, 3)

            row_idx += 1

        b_layout.addLayout(grid)
        layout.addWidget(body)

        # --- C. TOTALES ---
        total_bg = QFrame()
        total_bg.setObjectName("totalRowBg")
        t_layout = QHBoxLayout(total_bg)
        t_layout.setContentsMargins(16, 8, 16, 8)
        t_layout.setSpacing(10)

        t_lbl = QLabel("TOTALES:")
        t_lbl.setStyleSheet("font-weight: 700; font-size: 12px; color: #334155;")
        t_layout.addWidget(t_lbl)
        t_layout.addStretch()

        td = float(entry.get("total_debit", 0))
        tc = float(entry.get("total_credit", 0))

        td_lbl = QLabel(f"RD$ {td:,.2f}")
        td_lbl.setStyleSheet("font-weight: 800; color: #15803D; font-size: 13px;")
        td_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        td_lbl.setFixedWidth(110)
        t_layout.addWidget(td_lbl)

        tc_lbl = QLabel(f"RD$ {tc:,.2f}")
        tc_lbl.setStyleSheet("font-weight: 800; color: #DC2626; font-size: 13px;")
        tc_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        tc_lbl.setFixedWidth(110)
        t_layout.addWidget(tc_lbl)

        layout.addWidget(total_bg)

        # Metadata
        created_by = entry.get("created_by", "")
        if created_by:
            meta = QLabel(f"Creado por {created_by}")
            meta.setStyleSheet("font-size: 11px; color: #94A3B8; font-style: italic; margin-left: 16px; margin-bottom: 8px;")
            layout.addWidget(meta)

        return card

    def _mk_header(self, text, right=False):
        l = QLabel(text)
        l.setObjectName("colHeader")
        if right:
            l.setAlignment(Qt.AlignmentFlag.AlignRight)
        return l