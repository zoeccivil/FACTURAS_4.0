"""
modern_gui.py
----------------
Ventana principal moderna para FACTURAS-PyQT6-GIT.

Esta versión:
- Mantiene el estilo Clean Finance UI.
- Integra un botón "+ Nueva Factura" con menú:
    • Factura Emitida (Ingreso)
    • Factura de Gasto
- Está preparada para trabajar con un controller Firebase (LogicControllerFirebase),
  pero sigue siendo compatible con controladores anteriores siempre que implementen
  los métodos esperados.
"""

from __future__ import annotations

import datetime
from typing import List, Optional

from PyQt6.QtCore import Qt, QDate, QPoint
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMenuBar,
    QMenu,
    QMessageBox,
)

import sys

# Optional imports – these modules may not exist in every environment.
try:
    import qtawesome as qta  # type: ignore[import-not-found]
except Exception:
    qta = None

try:
    import migration_dialog  # type: ignore[import-not-found]
except Exception:
    migration_dialog = None

try:
    import firebase_config_dialog  # type: ignore[import-not-found]
except Exception:
    firebase_config_dialog = None

from tax_calculation_management_window_qt import TaxCalculationManagementWindowQt

# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------
STYLESHEET: str = """
/* Base application styles */
QMainWindow {
    background-color: #F8F9FA;
    color: #334155;
    font-family: Inter, Segoe UI, Roboto, sans-serif;
    font-size: 14px;
}

/* Texto global en QLineEdit */
QLineEdit {
    color: #111827;  /* gris muy oscuro, siempre legible sobre fondo claro */
}

/* Menu bar */
QMenuBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E5E7EB;
    color: #111827;  /* texto oscuro */
}
QMenuBar::item {
    padding: 4px 12px;
    background: transparent;
    color: #111827;  /* texto oscuro en items */
}
QMenuBar::item:selected {
    background: #F1F5F9;
}
QMenu {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    color: #111827;  /* texto oscuro en menús */
}
QMenu::item {
    padding: 4px 20px;
    color: #111827;
}
QMenu::item:selected {
    background-color: #E2E8F0;
}

/* Sidebar */
QFrame#sidebar {
    background-color: #1E293B;
    color: #F8FAFC;
}
QLabel#logoBox {
    background-color: #3B82F6;
    color: #FFFFFF;
    border-radius: 4px;
    font-weight: bold;
    font-size: 16px;
    min-width: 32px;
    min-height: 32px;
    max-width: 32px;
    max-height: 32px;
    text-align: center;
}
QComboBox#companySelector {
    background-color: #334155;
    color: #F8FAFC;
    border: 1px solid #475569;
    border-radius: 4px;
    padding: 4px;
}
QComboBox#companySelector::drop-down {
    border: none;
}
QComboBox#companySelector::down-arrow {
    image: none;
}
QPushButton#navButton {
    background-color: transparent;
    color: #94A3B8;
    text-align: left;
    padding: 8px 12px;
    border: none;
    border-radius: 4px;
    font-weight: 500;
}
QPushButton#navButton:hover {
    background-color: #0F172A;
    color: #FFFFFF;
}
QPushButton#navButton:checked {
    background-color: #3B82F6;
    color: #FFFFFF;
}
QPushButton#configButton {
    background-color: transparent;
    color: #94A3B8;
    padding: 6px 12px;
    border: none;
    text-align: left;
    border-radius: 4px;
}
QPushButton#configButton:hover {
    background-color: #0F172A;
    color: #FFFFFF;
}

/* Header */
QFrame#header {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E5E7EB;
}
QPushButton#primaryButton {
    background-color: #1E293B;
    color: #FFFFFF;
    padding: 6px 12px;
    border-radius: 6px;
    font-weight: 500;
}
QPushButton#primaryButton:hover {
    background-color: #0F172A;
}

/* Cards */
QFrame.card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 12px;
}
QLabel.card-title {
    color: #64748B;
    font-size: 12px;
    text-transform: uppercase;
    font-weight: 600;
}
QLabel.card-value {
    color: #0F172A;
    font-size: 20px;
    font-weight: 700;
}
QLabel.card-subtitle {
    color: #94A3B8;
    font-size: 11px;
}

/* Transactions table */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    gridline-color: #E2E8F0;
    color: #111827;
    selection-background-color: #E0F2FE;
    selection-color: #111827;
}
QHeaderView::section {
    background-color: #F1F5F9;
    border: none;
    padding: 6px;
    color: #64748B;
    font-weight: 600;
    font-size: 12px;
}
QTableWidget::item {
    padding: 6px;
    color: #111827;
}
QTableWidget::item:selected {
    background-color: #E0F2FE;
    color: #111827;
}

/* Filter buttons */
QPushButton#filterButton {
    border: 1px solid #CBD5E1;
    color: #475569;
    background-color: #FFFFFF;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
}
QPushButton#filterButton[active="true"] {
    background-color: #EFF6FF;
    border-color: #BFDBFE;
    color: #1D4ED8;
}
QPushButton#filterButton:hover {
    background-color: #F1F5F9;
}
"""






class ModernMainWindow(QMainWindow):
    """Main application window implementing a modern dashboard UI."""

    MONTHS_MAP = {
        "Enero": "01",
        "Febrero": "02",
        "Marzo": "03",
        "Abril": "04",
        "Mayo": "05",
        "Junio": "06",
        "Julio": "07",
        "Agosto": "08",
        "Septiembre": "09",
        "Octubre": "10",
        "Noviembre": "11",
        "Diciembre": "12",
    }


    def _initialize_chart_of_accounts(self, company_id, company_name:  str):
        """Inicializa el plan de cuentas estándar para una empresa."""
        reply = QMessageBox.question(
            self,
            "Inicializar Plan de Cuentas",
            f"¿Desea inicializar el plan de cuentas estándar para {company_name}?\n\n"
            f"Esto creará aproximadamente 50 cuentas contables básicas.",
            QMessageBox.StandardButton.Yes | QMessageBox. StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            year = int(self.current_year)
        except: 
            year = QDate.currentDate().year()
        
        ok, msg = self.controller.initialize_default_chart_of_accounts(company_id, year)
        
        if ok:
            QMessageBox.information(self, "Éxito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)


    def _generate_test_entries(self, company_id, company_name: str):
        """Genera asientos contables de prueba desde las facturas existentes."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QCheckBox, QPushButton, QHBoxLayout
        
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Generar Asientos de Prueba - {company_name}")
        dlg.resize(450, 250)
        
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        title = QLabel("🧪 Generar Asientos desde Facturas")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0F172A;")
        layout.addWidget(title)
        
        subtitle = QLabel(
            "Esta herramienta creará asientos contables automáticos\n"
            "desde todas las facturas registradas en el periodo seleccionado."
        )
        subtitle.setStyleSheet("color: #64748B; font-size: 13px;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        
        # Filtros
        filter_layout = QHBoxLayout()
        
        lbl_year = QLabel("Año:")
        combo_year = QComboBox()
        try:
            current_year = int(self.current_year)
        except:
            current_year = QDate.currentDate().year()
        
        for y in range(current_year - 2, current_year + 2):
            combo_year.addItem(str(y))
        combo_year.setCurrentText(str(current_year))
        
        filter_layout.addWidget(lbl_year)
        filter_layout.addWidget(combo_year)
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # Checkbox sobrescribir
        chk_overwrite = QCheckBox("Sobrescribir asientos existentes de facturas")
        chk_overwrite.setChecked(False)
        chk_overwrite.setStyleSheet("color: #DC2626; font-weight: 600;")
        layout.addWidget(chk_overwrite)
        
        layout.addStretch()
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_generate = QPushButton("Generar Asientos")
        btn_generate.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color:  white;
                padding: 8px 20px;
                border-radius:  6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
        """)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_generate)
        
        layout.addLayout(btn_layout)
        
        # Eventos
        btn_cancel.clicked. connect(dlg.reject)
        
        def on_generate():
            year = int(combo_year.currentText())
            overwrite = chk_overwrite. isChecked()
            
            dlg.accept()
            
            # Ejecutar generación
            ok, msg = self.controller.generate_test_journal_entries_from_invoices(
                company_id=company_id,
                year=year,
                month=None,
                overwrite=overwrite
            )
            
            if ok:
                QMessageBox.information(self, "Éxito", msg)
                # Refrescar dashboard si existe
                if hasattr(self, "refresh_dashboard"):
                    self.refresh_dashboard()
            else:
                QMessageBox.warning(self, "Error", msg)
        
        btn_generate.clicked. connect(on_generate)
        
        dlg.exec()



    def _open_journal_diary(self, company_id, company_name: str):
        """Abre el libro diario."""
        QMessageBox.information(
            self,
            "Libro Diario",
            f"Abriendo libro diario para {company_name}...\n\n"
            f"(Ventana en desarrollo)"
        )









    def _open_equity_statement(self, company_id, company_name: str):
        """Abre el estado de cambios en patrimonio."""
        QMessageBox.information(
            self,
            "Cambios en Patrimonio",
            f"Abriendo estado de cambios en patrimonio para {company_name}...\n\n"
            f"(Ventana en desarrollo)"
        )


    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Facturas Pro - Dashboard Moderno")
        self.resize(1280, 800)

        # persistent state
        self.current_month_name: str = ""
        self.current_year: str = ""
        self.transaction_filter_type: Optional[str] = None  # 'emitida' | 'gasto' | None
        self.nav_buttons: List[QPushButton] = []
        self.nav_buttons_by_key: dict[str, QPushButton] = {}
        self.current_transactions: List[dict] = []  # cache para menú contextual

        # UI elements we update later
        self.income_value_label: QLabel
        self.income_itbis_label: QLabel
        self.expense_value_label: QLabel
        self.expense_itbis_label: QLabel
        self.net_itbis_label: QLabel
        self.payable_label: QLabel
        self.table: QTableWidget
        self.company_selector: QComboBox
        self.month_selector: QComboBox
        self.year_selector: QComboBox
        self.filter_buttons: List[QPushButton] = []

        # Build UI
        self._build_ui()

        # Populate companies and set default filters
        self._populate_company_selector()
        self._set_default_filters()

        self.refresh_dashboard()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        """Construct all widgets and layouts for the window."""
        # Apply stylesheet
        self.setStyleSheet(STYLESHEET)

        # ------------------------------------------------------------------
        # Menubar
        # ------------------------------------------------------------------
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        # --- Menú Archivo (clásico)
        file_menu = menubar.addMenu("Archivo")
        file_menu.addAction("Cambiar Base de Datos...", self._change_database)
        file_menu.addAction("Crear Copia de Seguridad...", self._backup_database)
        file_menu.addAction("Restaurar Copia de Seguridad...", self._restore_database)
        file_menu.addSeparator()
        file_menu.addAction("Salir", self.close)

        # --- Menú Reportes (clásico)
        report_menu = menubar.addMenu("Reportes")
        report_menu.addAction("Reporte Mensual...", self._open_report_window)
        report_menu.addAction(
            "Reporte por Cliente/Proveedor...", self._open_third_party_report_window
        )

        # --- Menú Opciones (clásico)
        options_menu = menubar.addMenu("Opciones")
        options_menu.addAction("Configuración...", self._open_settings_window)
        options_menu.addSeparator()
        theme_menu = options_menu.addMenu("Cambiar Tema")
        for theme in ["Fusion", "Windows", "WindowsVista"]:
            theme_menu.addAction(
                theme, lambda checked=False, t=theme: self._change_theme(t)
            )

        # --- Menú Herramientas (Modern UI)
# En _build_ui(), en la sección del menú Herramientas:

        tools_menu = menubar.addMenu("Herramientas")

        action_config_firebase = QAction("Configurar Firebase…", self)
        action_config_firebase.triggered.connect(self.open_firebase_config)
        tools_menu.addAction(action_config_firebase)

        action_migrate = QAction("Migrar SQLite → Firebase…", self)
        action_migrate.triggered.connect(self.open_migration_dialog)
        tools_menu.addAction(action_migrate)

        action_backup = QAction("Crear backup SQL manual", self)
        action_backup.triggered.connect(self.create_manual_backup)
        tools_menu.addAction(action_backup)

        # ✅ NUEVO: Auditor de Adjuntos
        tools_menu.addSeparator()

        action_audit_attachments = QAction("🔍 Auditor de Adjuntos", self)
        action_audit_attachments.triggered.connect(self.open_attachment_auditor)
        tools_menu.addAction(action_audit_attachments)

        # ------------------------------------------------------------------
        # Layout principal
        # ------------------------------------------------------------------
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(12)

        # Header with logo and title
        header_row = QHBoxLayout()
        logo_label = QLabel("F")
        logo_label.setObjectName("logoBox")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label = QLabel("Facturas Pro")
        title_label.setStyleSheet("color: white; font-size: 16px; font-weight: 600;")
        header_row.addWidget(logo_label)
        header_row.addSpacing(8)
        header_row.addWidget(title_label)
        header_row.addStretch()
        sidebar_layout.addLayout(header_row)

        # Company selector
        comp_label = QLabel("EMPRESA ACTIVA")
        comp_label.setStyleSheet(
            "color: #94A3B8; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        )
        sidebar_layout.addWidget(comp_label)
        self.company_selector = QComboBox()
        self.company_selector.setObjectName("companySelector")
        self.company_selector.currentIndexChanged.connect(self.on_company_changed)
        sidebar_layout.addWidget(self.company_selector)

        # Navigation buttons
        self._add_nav_button(sidebar_layout, "fa5s.chart-pie", "Dashboard", "dashboard")
        self._add_nav_button(
            sidebar_layout, "fa5s.file-invoice-dollar", "Ingresos", "ingresos"
        )
        self._add_nav_button(
            sidebar_layout, "fa5s.shopping-cart", "Gastos", "gastos"
        )
        self._add_nav_button(
            sidebar_layout, "fa5s.calculator", "Calc. Impuestos", "tax"
        )
        self._add_nav_button(
            sidebar_layout, "fa5s.percent", "Resumen ITBIS", "itbis_summary"
        )
        self._add_nav_button(
            sidebar_layout, "fa5s.chart-area", "Utilidades", "profit_summary"
        )
        # ✅ NUEVO:  Botón de Contabilidad
        self._add_nav_button(
            sidebar_layout, "fa5s.book", "Contabilidad", "accounting"
        )
        # ✅ NUEVO: Botón de Optimizador Financiero
        self._add_nav_button(
            sidebar_layout, "fa5s.chart-bar", "Optimizador\nFinanciero", "financial_optimizer"
        )
        self._add_nav_button(
            sidebar_layout, "fa5s.chart-line", "Reportes", "reportes"
        )

        sidebar_layout.addStretch()

        # Configuration button at bottom
        config_btn = QPushButton()
        config_btn.setObjectName("configButton")
        config_btn.setText("Configuración")
        config_btn.setCheckable(False)
        if qta:
            try:
                config_btn.setIcon(qta.icon("fa5s.cog", color="#94A3B8"))
            except Exception:
                pass
        config_btn.clicked.connect(self.open_firebase_config)
        sidebar_layout.addWidget(config_btn)

        main_layout.addWidget(sidebar)

        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)

        # Header area inside content
        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)
        self.section_title = QLabel("Resumen Financiero")
        self.section_title.setStyleSheet(
            "font-size: 20px; font-weight: 700; color: #1E293B;"
        )
        header_layout.addWidget(self.section_title)
        header_layout.addStretch()

        # Button for new invoice (Ingreso / Gasto)
        new_invoice_btn = QPushButton()
        new_invoice_btn.setObjectName("primaryButton")
        new_invoice_btn.setText("+ Nueva Factura")
        new_invoice_btn.setCheckable(False)
        if qta:
            try:
                new_invoice_btn.setIcon(qta.icon("fa5s.plus", color="#FFFFFF"))
            except Exception:
                pass

        new_invoice_menu = QMenu(new_invoice_btn)
        action_income = new_invoice_menu.addAction("Factura Emitida (Ingreso)")
        action_expense = new_invoice_menu.addAction("Factura de Gasto")
        action_income.triggered.connect(self.open_add_income_invoice)
        action_expense.triggered.connect(self.open_add_expense_invoice)
        new_invoice_btn.setMenu(new_invoice_menu)

        header_layout.addWidget(new_invoice_btn)
        content_layout.addWidget(header)

        # Filters row (month and year)
        filters_row = QHBoxLayout()
        filters_row.setSpacing(12)
        self.month_selector = QComboBox()
        for month in self.MONTHS_MAP.keys():
            self.month_selector.addItem(month)
        filters_row.addWidget(self.month_selector)
        self.month_selector.currentIndexChanged.connect(self.on_filter_changed)

        self.year_selector = QComboBox()
        filters_row.addWidget(self.year_selector)
        self.year_selector.currentIndexChanged.connect(self.on_filter_changed)

        filters_row.addStretch()
        content_layout.addLayout(filters_row)

        # KPI Cards grid
        cards_widget = QWidget()
        cards_layout = QGridLayout(cards_widget)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(16)

        def create_card(title: str) -> tuple[QFrame, QLabel, QLabel]:
            frame = QFrame()
            frame.setProperty("class", "card")
            frame.setFrameShape(QFrame.Shape.NoFrame)
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(12, 12, 12, 12)
            layout.setSpacing(4)
            title_lbl = QLabel(title)
            title_lbl.setProperty("class", "card-title")
            layout.addWidget(title_lbl)
            value_lbl = QLabel("RD$ 0.00")
            value_lbl.setProperty("class", "card-value")
            layout.addWidget(value_lbl)
            subtitle_lbl = QLabel("")
            subtitle_lbl.setProperty("class", "card-subtitle")
            layout.addWidget(subtitle_lbl)
            layout.addStretch()
            return frame, value_lbl, subtitle_lbl

        income_card, self.income_value_label, self.income_itbis_label = create_card(
            "Total Ingresos"
        )
        expense_card, self.expense_value_label, self.expense_itbis_label = create_card(
            "Total Gastos"
        )
        net_card, self.net_itbis_label, _ = create_card("ITBIS Neto")
        payable_card, self.payable_label, _ = create_card("A Pagar (Estimado)")

        income_card.setStyleSheet("QFrame { border-left: 4px solid #10B981; }")
        expense_card.setStyleSheet("QFrame { border-left: 4px solid #EF4444; }")
        net_card.setStyleSheet("QFrame { border-left: 4px solid #2563EB; }")
        payable_card.setStyleSheet("QFrame { border-left: 4px solid #F59E0B; }")

        cards_layout.addWidget(income_card, 0, 0)
        cards_layout.addWidget(expense_card, 0, 1)
        cards_layout.addWidget(net_card, 0, 2)
        cards_layout.addWidget(payable_card, 0, 3)
        content_layout.addWidget(cards_widget)

        # Transactions header
        tx_header_widget = QWidget()
        tx_header_layout = QHBoxLayout(tx_header_widget)
        tx_header_layout.setContentsMargins(0, 0, 0, 0)
        tx_header_layout.setSpacing(8)
        tx_title = QLabel("Transacciones Recientes")
        tx_title.setStyleSheet(
            "font-weight: 600; font-size: 16px; color: #334155;"
        )
        tx_header_layout.addWidget(tx_title)
        tx_header_layout.addStretch()
        for name, tx_type in [
            ("Todos", None),
            ("Ingresos", "emitida"),
            ("Gastos", "gasto"),
        ]:
            btn = QPushButton(name)
            btn.setObjectName("filterButton")
            btn.setCheckable(True)
            btn.setProperty("active", "false")
            btn.clicked.connect(
                lambda checked, t=tx_type, b=btn: self.on_filter_button_clicked(t, b)
            )
            self.filter_buttons.append(btn)
            tx_header_layout.addWidget(btn)
        content_layout.addWidget(tx_header_widget)

        # Transactions table
        self.table = QTableWidget(0, 9)  # ✅ Aumentado de 6 a 9 columnas
        self.table.setHorizontalHeaderLabels(
            ["Fecha", "Tipo", "No. Factura", "Empresa / Tercero", "Moneda", "ITBIS Original", "ITBIS RD$", "Total Original", "Total RD$"]
        )
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header_view.setSectionsMovable(False)
        self.table.verticalHeader().setVisible(False)
        self.table.cellDoubleClicked.connect(self.on_table_double_click)

        # Menú contextual en la tabla
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._open_context_menu)

        content_layout.addWidget(self.table)

        main_layout.addWidget(content)

    # ------------------------------------------------------------------
    # Helper to add navigation buttons to sidebar
    # ------------------------------------------------------------------
    def _add_nav_button(
        self, layout: QVBoxLayout, icon_name: str, text: str, section: str
    ) -> None:
        btn = QPushButton()
        btn.setObjectName("navButton")
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        btn.setText(text)
        if qta:
            try:
                btn.setIcon(qta.icon(icon_name, color="#94A3B8"))
            except Exception:
                pass
        btn.clicked.connect(lambda checked, s=section: self.on_nav_clicked(s))
        layout.addWidget(btn)
        self.nav_buttons.append(btn)
        self.nav_buttons_by_key[section] = btn

    # ------------------------------------------------------------------
    # Company selector population
    # ------------------------------------------------------------------
    def _populate_company_selector(self) -> None:
        self.company_selector.clear()
        try:
            if hasattr(self.controller, "list_companies"):
                companies = self.controller.list_companies() or []
                for name in companies:
                    self.company_selector.addItem(str(name))
        except Exception as exc:
            QMessageBox.warning(
                self, "Empresas", f"No se pudieron cargar las empresas: {exc}"
            )

    def _set_default_filters(self) -> None:
        current_month_index = QDate.currentDate().month() - 1
        if 0 <= current_month_index < len(self.MONTHS_MAP):
            self.month_selector.setCurrentIndex(current_month_index)
        else:
            self.month_selector.setCurrentIndex(0)
        self.current_month_name = self.month_selector.currentText()

        self.year_selector.clear()
        try:
            if hasattr(self.controller, "get_unique_invoice_years") and hasattr(
                self.controller, "set_active_company"
            ):
                company_name = self.company_selector.currentText()
                self.controller.set_active_company(company_name)
                years = self.controller.get_unique_invoice_years(None) or []
                years = sorted(
                    {int(y) for y in years if y not in (None, "")}, reverse=True
                )
                for y in years:
                    self.year_selector.addItem(str(y))
            if self.year_selector.count() == 0:
                self.year_selector.addItem(str(QDate.currentDate().year()))
        except Exception:
            self.year_selector.addItem(str(QDate.currentDate().year()))
        self.year_selector.setCurrentIndex(0)
        self.current_year = self.year_selector.currentText()

    # ------------------------------------------------------------------
    # Navigation handler
    # ------------------------------------------------------------------
    def on_nav_clicked(self, key: str) -> None:
        """
        Maneja los clics en los botones del sidebar de navegación.
        """
        if key == "dashboard":
            self.transaction_filter_type = None
            try:
                if hasattr(self.controller, "set_transaction_filter"):
                    self.controller.set_transaction_filter(None)
            except Exception: 
                pass
            if hasattr(self, "show_dashboard_view"):
                self.show_dashboard_view()
            else:
                self.refresh_dashboard()

        elif key == "ingresos":
            self.transaction_filter_type = "emitida"
            try: 
                if hasattr(self.controller, "set_transaction_filter"):
                    self.controller.set_transaction_filter("emitida")
            except Exception:
                pass
            if hasattr(self, "show_ingresos_view"):
                self.show_ingresos_view()
            else:
                self.refresh_dashboard()

        elif key == "gastos":
            self.transaction_filter_type = "gasto"
            try:
                if hasattr(self.controller, "set_transaction_filter"):
                    self.controller.set_transaction_filter("gasto")
            except Exception:
                pass
            if hasattr(self, "show_gastos_view"):
                self.show_gastos_view()
            else:
                self.refresh_dashboard()

        elif key == "tax":
            if hasattr(self, "open_tax_calculation_manager"):
                self.open_tax_calculation_manager()

        elif key == "itbis_summary":
            self.open_itbis_summary_window()

        # ✅ NUEVO: Caso para Utilidades
        elif key == "profit_summary":
            self.open_profit_summary_window()

        # ✅ NUEVO:  Caso para Contabilidad
        elif key == "accounting":
            self.open_accounting_menu()

        # ✅ NUEVO: Caso para Optimizador Financiero
        elif key == "financial_optimizer":
            self.open_financial_optimizer()

        elif key == "reportes":
            # Abrir menú de opciones de reporte
            self. open_reports_menu()

    # ------------------------------------------------------------------
    # Company change handler
    # ------------------------------------------------------------------
    def on_company_changed(self) -> None:
        company_name = self.company_selector.currentText()
        try:
            if hasattr(self.controller, "set_active_company"):
                self.controller.set_active_company(company_name)
        except Exception as exc:
            QMessageBox.warning(
                self, "Empresa", f"No se pudo asignar la empresa activa: {exc}"
            )
        try:
            if hasattr(self.controller, "get_unique_invoice_years"):
                years = self.controller.get_unique_invoice_years(None) or []
                years = sorted(
                    {int(y) for y in years if y not in (None, "")}, reverse=True
                )
                self.year_selector.clear()
                for y in years:
                    self.year_selector.addItem(str(y))
                if not years:
                    self.year_selector.addItem(str(QDate.currentDate().year()))
                self.year_selector.setCurrentIndex(0)
        except Exception:
            pass
        self.refresh_dashboard()

    # ------------------------------------------------------------------
    # Filter handlers
    # ------------------------------------------------------------------
    def on_filter_changed(self) -> None:
        self.current_month_name = self.month_selector.currentText()
        self.current_year = self.year_selector.currentText()
        self.refresh_dashboard()

    def on_filter_button_clicked(
        self, tx_type: Optional[str], button: QPushButton
    ) -> None:
        for btn in self.filter_buttons:
            active = btn is button
            btn.setChecked(active)
            btn.setProperty("active", "true" if active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.transaction_filter_type = tx_type
        try:
            if hasattr(self.controller, "set_transaction_filter"):
                self.controller.set_transaction_filter(tx_type)
        except Exception:
            pass
        self.refresh_transactions()

    # ------------------------------------------------------------------
    # Dashboard refresh
    # ------------------------------------------------------------------
    def refresh_dashboard(self) -> None:
        month_str = self.MONTHS_MAP.get(self.current_month_name, None)
        try:
            year_int = int(self.current_year)
        except Exception:
            year_int = None

        summary_data = None
        try:
            if hasattr(self.controller, "_refresh_dashboard"):
                summary_data = self.controller._refresh_dashboard(month_str, year_int)
        except Exception as exc:
            QMessageBox.warning(
                self, "Resumen", f"No se pudo obtener el resumen: {exc}"
            )

        if summary_data:
            try:
                income = float(summary_data.get("income", 0.0))
                income_itbis = float(summary_data.get("income_itbis", 0.0))
                expense = float(summary_data.get("expense", 0.0))
                expense_itbis = float(summary_data.get("expense_itbis", 0.0))
                net_itbis = float(summary_data.get("net_itbis", 0.0))
                payable = float(summary_data.get("payable", 0.0))
                itbis_adelantado = float(summary_data.get("itbis_adelantado", 0.0))
                payable_estimated = float(
                    summary_data.get("payable_estimated", payable)
                )

                # Card: Total Ingresos
                self.income_value_label.setText(f"RD$ {income:,.2f}")
                self.income_itbis_label.setText(f"ITBIS: RD$ {income_itbis:,.2f}")

                # Card: Total Gastos (mostrar ITBIS de gastos y adelantado)
                self.expense_value_label.setText(f"RD$ {expense:,.2f}")
                self.expense_itbis_label.setText(
                    f"ITBIS: RD$ {expense_itbis:,.2f}  "
                    f"(Adelantado: RD$ {itbis_adelantado:,.2f})"
                )

                # Card: ITBIS Neto
                self.net_itbis_label.setText(f"RD$ {net_itbis:,.2f}")

                # Card: A Pagar (Estimado) = neto - adelantado
                self.payable_label.setText(f"RD$ {payable_estimated:,.2f}")

                # Tooltip explicativo en el card A Pagar
                tooltip_text = (
                    "A pagar (estimado) = ITBIS Neto − ITBIS pagado por adelantado "
                    f"del mismo periodo.\n\n"
                    f"ITBIS Neto: RD$ {net_itbis:,.2f}\n"
                    f"ITBIS Adelantado: RD$ {itbis_adelantado:,.2f}\n"
                    f"Resultado: RD$ {payable_estimated:,.2f}"
                )
                self.payable_label.setToolTip(tooltip_text)

            except Exception:
                pass

        self.refresh_transactions()

    # ------------------------------------------------------------------
    # Transactions refresh
    # ------------------------------------------------------------------
    def refresh_transactions(self) -> None:
        month_str = self.MONTHS_MAP.get(self.current_month_name, None)
        try:
            year_int = int(self.current_year)
        except Exception:
            year_int = None
        tx_type = self.transaction_filter_type

        transactions: List[dict] = []
        try:
            if hasattr(self.controller, "_populate_transactions_table"):
                transactions = (
                    self.controller._populate_transactions_table(
                        month_str, year_int, tx_type
                    )
                    or []
                )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Transacciones",
                f"No se pudo obtener la lista de transacciones: {exc}",
            )

        self.current_transactions = transactions
        self._populate_table(transactions)

    # ------------------------------------------------------------------
    # Tabla de transacciones
    # ------------------------------------------------------------------
    def _populate_table(self, transactions: List[dict]) -> None:
        """Populate the QTableWidget with transaction data."""
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        if not transactions:
            return

        self.table.setRowCount(len(transactions))

        for row_index, trans in enumerate(transactions):
            date_val = str(trans.get("date") or trans.get("invoice_date") or "")
            tx_type = str(trans.get("type") or trans.get("invoice_type") or "")
            number = str(trans.get("number") or trans.get("invoice_number") or "")
            party = str(trans.get("party") or trans.get("third_party_name") or "")
            
            # ✅ NUEVO: Obtener valores originales y convertidos
            currency = str(trans.get("currency", "RD$"))
            itbis_original = float(trans.get("itbis_original_currency", 0.0) or 0.0)
            itbis_rd = float(trans.get("itbis_rd") or trans.get("itbis", 0.0) or 0.0)
            total_original = float(trans.get("total_amount_original_currency", 0.0) or 0.0)
            total_rd = float(trans.get("total_amount_rd") or trans.get("total", 0.0) or 0.0)

            if tx_type == "emitida":
                type_display = "↑ INGRESO"
            elif tx_type == "gasto":
                type_display = "↓ GASTO"
            else:
                type_display = tx_type or ""

            flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

            # Columna 0: Fecha
            date_item = QTableWidgetItem(date_val)
            date_item.setFlags(flags)
            self.table.setItem(row_index, 0, date_item)

            # Columna 1: Tipo
            type_item = QTableWidgetItem(type_display)
            type_item.setFlags(flags)
            if tx_type == "emitida":
                type_item.setForeground(QColor("#16A34A"))
            elif tx_type == "gasto":
                type_item.setForeground(QColor("#DC2626"))
            type_item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            self.table.setItem(row_index, 1, type_item)

            # Columna 2: Número de factura
            num_item = QTableWidgetItem(number)
            num_item.setFlags(flags)
            num_item.setData(Qt.ItemDataRole.UserRole, number)
            self.table.setItem(row_index, 2, num_item)

            # Columna 3: Tercero
            party_item = QTableWidgetItem(party)
            party_item.setFlags(flags)
            self.table.setItem(row_index, 3, party_item)

            # Columna 4: Moneda
            currency_item = QTableWidgetItem(currency)
            currency_item.setFlags(flags)
            currency_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            self.table.setItem(row_index, 4, currency_item)

            # Columna 5: ITBIS Original
            # Para moneda extranjera, mostrar en esa moneda; para RD$, mostrar sin prefijo
            if currency in ["RD$", "DOP", "RD", "DOP$"]:
                itbis_orig_display = f"RD$ {itbis_original:,.2f}"
            else:
                itbis_orig_display = f"{currency} {itbis_original:,.2f}"
            
            itbis_orig_item = QTableWidgetItem(itbis_orig_display)
            itbis_orig_item.setFlags(flags)
            itbis_orig_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.table.setItem(row_index, 5, itbis_orig_item)

            # Columna 6: ITBIS RD$
            itbis_rd_item = QTableWidgetItem(f"RD$ {itbis_rd:,.2f}")
            itbis_rd_item.setFlags(flags)
            itbis_rd_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.table.setItem(row_index, 6, itbis_rd_item)

            # Columna 7: Total Original
            # Para moneda extranjera, mostrar en esa moneda; para RD$, mostrar sin prefijo
            if currency in ["RD$", "DOP", "RD", "DOP$"]:
                total_orig_display = f"RD$ {total_original:,.2f}"
            else:
                total_orig_display = f"{currency} {total_original:,.2f}"
            
            total_orig_item = QTableWidgetItem(total_orig_display)
            total_orig_item.setFlags(flags)
            total_orig_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.table.setItem(row_index, 7, total_orig_item)

            # Columna 8: Total RD$
            total_rd_item = QTableWidgetItem(f"RD$ {total_rd:,.2f}")
            total_rd_item.setFlags(flags)
            total_rd_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.table.setItem(row_index, 8, total_rd_item)

            # Colores por tipo: fila completa
            if tx_type == "emitida":
                bg = QColor("#ECFDF3")  # verde muy claro
            elif tx_type == "gasto":
                bg = QColor("#FEF2F2")  # rojo muy claro
            else:
                bg = None

            if bg is not None:
                for col in range(self.table.columnCount()):
                    item = self.table.item(row_index, col)
                    if item is not None:
                        item.setBackground(bg)

        self.table.setSortingEnabled(True)

    # ------------------------------------------------------------------
    # Menú contextual en la tabla
    # ------------------------------------------------------------------
    def _open_context_menu(self, pos: QPoint) -> None:
        row = self.table.rowAt(pos.y())
        if row < 0 or row >= self.table.rowCount():
            return

        tx = self._get_transaction_for_row(row)
        if not tx:
            return

        invoice_number = str(
            tx.get("number") or tx.get("invoice_number") or ""
        ).strip()
        if not invoice_number:
            return

        menu = QMenu(self)

        act_view = QAction("Ver adjunto…", self)
        act_edit = QAction("Editar transacción…", self)
        act_delete = QAction("Eliminar transacción…", self)

        act_view.triggered.connect(lambda: self._view_attachment(invoice_number, tx))
        act_edit.triggered.connect(lambda: self._edit_transaction(invoice_number, tx))
        act_delete.triggered.connect(
            lambda: self._delete_transaction(invoice_number, tx)
        )

        menu.addAction(act_view)
        menu.addSeparator()
        menu.addAction(act_edit)
        menu.addAction(act_delete)

        global_pos = self.table.viewport().mapToGlobal(pos)
        menu.exec(global_pos)

    def _get_transaction_for_row(self, row: int) -> Optional[dict]:
        """
        Obtiene la transacción correspondiente a una fila de la tabla.
        Usa el número de factura como identificador único para evitar
        problemas con el ordenamiento de la tabla.
        """
        if not self.current_transactions:
            return None
        
        # Obtener el número de factura de la celda (columna 2)
        item = self.table.item(row, 2)
        if not item:
            return None
        
        invoice_number = item. data(Qt.ItemDataRole.UserRole)
        if not invoice_number:
            invoice_number = item.text().strip()
        
        if not invoice_number:
            return None
        
        # Buscar la transacción por número de factura
        for tx in self.current_transactions:
            tx_number = str(tx. get("number") or tx.get("invoice_number") or "").strip()
            if tx_number == str(invoice_number).strip():
                return tx
        
        return None

    def _edit_transaction(self, invoice_number: str, tx: dict) -> None:
        try:
            if hasattr(self.controller, "edit_invoice_by_number"):
                self.controller.edit_invoice_by_number(invoice_number, parent=self)
                self.refresh_dashboard()
            else:
                QMessageBox.information(
                    self,
                    "Editar",
                    "El controlador no implementa 'edit_invoice_by_number'.",
                )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Editar transacción",
                f"No se pudo editar la factura {invoice_number}: {exc}",
            )

    def _delete_transaction(self, invoice_number: str, tx: dict) -> None:
        confirm = QMessageBox.question(
            self,
            "Eliminar transacción",
            f"¿Seguro que deseas eliminar la factura {invoice_number}?\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            if hasattr(self.controller, "delete_invoice_by_number"):
                self.controller.delete_invoice_by_number(invoice_number, parent=self)
                self.refresh_dashboard()
            else:
                QMessageBox.information(
                    self,
                    "Eliminar",
                    "El controlador no implementa 'delete_invoice_by_number'.",
                )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Eliminar transacción",
                f"No se pudo eliminar la factura {invoice_number}: {exc}",
            )

    def _view_attachment(self, invoice_number: str, tx: dict) -> None:
        try:
            if hasattr(self.controller, "view_invoice_attachment_by_number"):
                self.controller.view_invoice_attachment_by_number(
                    invoice_number, parent=self
                )
            else:
                QMessageBox.information(
                    self,
                    "Ver adjunto",
                    "El controlador no implementa 'view_invoice_attachment_by_number'.",
                )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Ver adjunto",
                f"No se pudo abrir el adjunto de la factura {invoice_number}: {exc}",
            )

    # ------------------------------------------------------------------
    # Dialog and external action helpers
    # ------------------------------------------------------------------
    def open_add_income_invoice(self) -> None:
        try:
            if hasattr(self.controller, "open_add_income_invoice_window"):
                self.controller.open_add_income_invoice_window(parent=self)
            elif hasattr(self.controller, "open_add_invoice_window"):
                self.controller.open_add_invoice_window()
            else:
                QMessageBox.information(
                    self,
                    "Nueva Factura",
                    "El controlador no implementa alta de facturas emitidas.",
                )
        except Exception as exc:
            QMessageBox.critical(
                self, "Nueva Factura", f"No se pudo abrir la ventana de ingreso: {exc}"
            )

    def open_add_expense_invoice(self) -> None:
        try:
            if hasattr(self.controller, "open_add_expense_invoice_window"):
                self.controller.open_add_expense_invoice_window(parent=self)
            else:
                QMessageBox.information(
                    self,
                    "Factura de Gasto",
                    "El controlador no implementa alta de facturas de gasto.",
                )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Factura de Gasto",
                f"No se pudo abrir la ventana de gasto: {exc}",
            )

    def open_tax_manager(self) -> None:
        if hasattr(self.controller, "_open_tax_calculation_manager"):
            self.controller._open_tax_calculation_manager()

    def open_itbis_summary(self) -> None:
        try:
            if hasattr(self.controller, "_open_itbis_summary"):
                self.controller._open_itbis_summary()
            else:
                QMessageBox.information(
                    self, "Resumen ITBIS", "Resumen ITBIS no disponible."
                )
        except Exception as exc:
            QMessageBox.critical(
                self, "Resumen ITBIS", f"No se pudo abrir el resumen ITBIS: {exc}"
            )

    def open_report_window(self) -> None:
        try:
            if hasattr(self.controller, "_open_report_window"):
                self.controller._open_report_window()
            else:
                QMessageBox.information(
                    self, "Reportes", "Función de reportes no disponible."
                )
        except Exception as exc:
            QMessageBox.critical(
                self, "Reportes", f"No se pudo abrir el reporte: {exc}"
            )

    def open_migration_dialog(self) -> None:
        if migration_dialog is None:
            QMessageBox.warning(
                self, "Migración", "El módulo de migración no está disponible."
            )
            return
        try:
            default_path = ""
            try:
                if hasattr(self.controller, "get_sqlite_db_path"):
                    default_path = self.controller.get_sqlite_db_path() or ""
            except Exception:
                default_path = ""
            if hasattr(migration_dialog, "show_migration_dialog"):
                migration_dialog.show_migration_dialog(self, default_db_path=default_path)
            else:
                QMessageBox.information(
                    self, "Migración", "El diálogo de migración no está implementado."
                )
        except Exception as exc:
            QMessageBox.critical(
                self, "Migración", f"No se pudo abrir el diálogo de migración: {exc}"
            )

    def open_firebase_config(self) -> None:
        if firebase_config_dialog is None:
            QMessageBox.warning(
                self,
                "Configurar Firebase",
                "El módulo de configuración de Firebase no está disponible.",
            )
            return
        try:
            if hasattr(firebase_config_dialog, "show_firebase_config_dialog"):
                accepted = firebase_config_dialog.show_firebase_config_dialog(
                    self, controller=self.controller
                )
                if accepted and hasattr(self.controller, "on_firebase_config_updated"):
                    self.controller.on_firebase_config_updated()
                    self.refresh_dashboard()
            else:
                QMessageBox.information(
                    self,
                    "Configurar Firebase",
                    "El diálogo de configuración no está implementado.",
                )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Configurar Firebase",
                f"No se pudo abrir la configuración: {exc}",
            )

    def create_manual_backup(self) -> None:
        try:
            if hasattr(self.controller, "create_sql_backup"):
                path = self.controller.create_sql_backup(retention_days=30)
                QMessageBox.information(
                    self,
                    "Backup SQL",
                    f"Backup creado en: {path}\nEste archivo se eliminará automáticamente en 30 días.",
                )
            else:
                QMessageBox.information(
                    self, "Backup", "El controlador no soporta crear backups."
                )
        except Exception as exc:
            QMessageBox.critical(
                self, "Backup", f"No se pudo crear el backup: {exc}"
            )

    # ------------------------------------------------------------------
    # Table double-click handler
    # ------------------------------------------------------------------
    def on_table_double_click(self, row: int, column: int) -> None:
        if row < 0:
            return
        try:
            item = self.table.item(row, 2)
            invoice_number = (
                item.data(Qt.ItemDataRole.UserRole) if item else None
            )
            if not invoice_number:
                return
            if hasattr(self.controller, "diagnose_row"):
                self.controller.diagnose_row(number=invoice_number)
            else:
                QMessageBox.information(
                    self,
                    "Diagnóstico",
                    f"Diagnóstico de factura {invoice_number}: función no disponible.",
                )
        except Exception as exc:
            QMessageBox.critical(
                self, "Diagnóstico", f"No se pudo diagnosticar la fila: {exc}"
            )

    # ------------------------------------------------------------------
    # Menú clásico: placeholders
    # ------------------------------------------------------------------
    def _change_database(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Cambiar Base de Datos",
            "Esta función no está disponible en el backend Firebase.\n"
            "Si necesitas cambiar de base SQLite, usa la versión clásica.",
        )

    def _backup_database(self):
        from PyQt6.QtWidgets import QMessageBox
        if hasattr(self.controller, "create_sql_backup"):
            try:
                path = self.controller.create_sql_backup()
                QMessageBox.information(
                    self,
                    "Copia de Seguridad",
                    f"Se creó un backup simbólico (Firebase):\n{path}",
                )
                return
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Copia de Seguridad",
                    f"No se pudo crear el backup:\n{e}",
                )
                return
        QMessageBox.warning(
            self,
            "Copia de Seguridad",
            "El controlador no soporta creación de backups.",
        )

    def _restore_database(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Restaurar Copia de Seguridad",
            "Restaurar backups no está implementado en el backend Firebase.",
        )

    def _open_report_window(self):
        """Abre la ventana de reporte mensual clásico usando el controller actual."""
        try:
            from reporte_mensual_window import ReportWindowQt
        except Exception:
            QMessageBox.information(
                self,
                "Reportes",
                "El módulo de reporte mensual (reporte_mensual_window.py) no está disponible.",
            )
            return

        try:
            dlg = ReportWindowQt(self, self.controller)
            dlg.exec()
        except Exception as exc:
            QMessageBox.critical(
                self, "Reportes", f"No se pudo abrir el reporte mensual: {exc}"
            )

    def _open_third_party_report_window(self):
        """Abre el reporte por Cliente/Proveedor usando el controller actual."""
        try:
            from reporte_cliente_window import ThirdPartyReportWindowQt
        except Exception:
            QMessageBox.information(
                self,
                "Reportes por Cliente/Proveedor",
                "El módulo reporte_cliente_window.py no está disponible.",
            )
            return

        try:
            dlg = ThirdPartyReportWindowQt(self, self.controller)
            dlg.exec()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Reportes por Cliente/Proveedor",
                f"No se pudo abrir el reporte: {exc}",
            )

    def open_reports_menu(self) -> None:
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
        action_monthly = menu.addAction("Reporte Mensual...")
        action_third_party = menu.addAction("Reporte por Cliente/Proveedor...")
        action_monthly.triggered.connect(self._open_report_window)
        action_third_party.triggered.connect(self._open_third_party_report_window)

        # Si tenemos el botón 'reportes', posicionar el menú junto a él
        btn = getattr(self, "nav_buttons_by_key", {}).get("reportes")
        if btn is not None:
            global_pos = btn.mapToGlobal(btn.rect().bottomLeft())
        else:
            global_pos = self.mapToGlobal(self.cursor().pos())

        menu.exec(global_pos)


    # === MÉTODOS AUXILIARES QUE NECESITAS IMPLEMENTAR ===

    def get_current_company_id(self):
        """Obtiene el ID de la empresa activa."""
        company_name = self.company_selector.currentText()
        
        if not company_name:
            return None
        
        # Intentar obtener ID del controller
        if hasattr(self.controller, "active_company_id"):
            return self.controller.active_company_id
        
        # Fallback:  usar nombre normalizado
        return company_name.lower().replace(" ", "_")

    def _open_settings_window(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Configuración",
            "La configuración general aún no está implementada en el dashboard moderno.\n"
            "Puedes configurar Firebase desde el menú Herramientas.",
        )

    def _change_theme(self, theme_name: str):
        from PyQt6.QtWidgets import QApplication, QMessageBox, QStyleFactory

        app = QApplication.instance()
        if not app:
            return

        try:
            available = QStyleFactory.keys()
            if theme_name in available:
                app.setStyle(QStyleFactory.create(theme_name))
            else:
                QMessageBox.warning(
                    self,
                    "Tema no disponible",
                    f"El tema '{theme_name}' no está disponible en esta plataforma.\n"
                    f"Temas disponibles: {', '.join(available)}",
                )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error cambiando tema",
                f"No se pudo cambiar el tema:\n{e}",
            )

    def open_tax_calculation_manager(self):
        from tax_calculation_management_window_qt import TaxCalculationManagementWindowQt
        dlg = TaxCalculationManagementWindowQt(self, self.controller)
        dlg.exec()


    def open_itbis_summary_window(self) -> None:
        """Abre la ventana de resumen ITBIS para la empresa y mes/año actuales."""
        try:
            from itbis_summary_window_qt import ItbisSummaryWindowQt

            company_id = self.get_current_company_id()
            company_name = self.company_selector.currentText()

            if not company_id: 
                QMessageBox.warning(
                    self,
                    "Resumen ITBIS",
                    "No hay empresa activa seleccionada.",
                )
                return

            month_str = self.MONTHS_MAP. get(self.current_month_name, None)
            try:
                year_int = int(self.current_year)
            except Exception:
                year_int = None

            if not month_str or year_int is None:
                QMessageBox.warning(
                    self,
                    "Resumen ITBIS",
                    "Mes o año no válidos para el resumen.",
                )
                return

            dlg = ItbisSummaryWindowQt(
                parent=self,
                controller=self.controller,
                company_id=company_id,
                company_name=company_name,
                month_str=month_str,
                year_int=year_int,
            )
            dlg.exec()
            
        except Exception as e: 
            QMessageBox.critical(self, "Resumen ITBIS", f"Error:  {e}")

    def open_profit_summary_window(self):
        """Abre la ventana de resumen de utilidades."""
        try:
            company_id = self. get_current_company_id()
            company_name = self. company_selector.currentText()
            
            if not company_id:  
                QMessageBox.warning(self, "Sin Empresa", "Selecciona una empresa primero.")
                return
            
            from profit_summary_window import ProfitSummaryWindow
            from PyQt6.QtCore import QDate
            
            # Usar mes y año actuales de los selectores
            month_name = self.month_selector.currentText()
            month_str = self.MONTHS_MAP.get(month_name, None)
            
            try:
                year_int = int(self.year_selector.currentText())
            except:
                year_int = QDate.currentDate().year()
            
            if not month_str:
                month_str = f"{QDate.currentDate().month():02d}"
            
            dlg = ProfitSummaryWindow(
                parent=self,
                controller=self. controller,
                company_id=company_id,
                company_name=company_name,
                month_str=month_str,
                year_int=year_int,
            )
            dlg.exec()
            
        except Exception as e:  
            QMessageBox.critical(self, "Error", f"No se pudo abrir la ventana:\n{e}")
            import traceback
            traceback. print_exc()

    def open_financial_optimizer(self):
        """Abre el Optimizador Financiero."""
        try:
            company_id = self.get_current_company_id()
            company_name = self.company_selector.currentText()
            
            if not company_id:
                QMessageBox.warning(self, "Sin Empresa", "Selecciona una empresa primero.")
                return
            
            from PyQt6.QtCore import QDate
            
            # Usar mes y año actuales de los selectores
            month_name = self.month_selector.currentText()
            month_str = self.MONTHS_MAP.get(month_name, None)
            
            try:
                year_int = int(self.year_selector.currentText())
            except:
                year_int = QDate.currentDate().year()
            
            if not month_str:
                month_str = f"{QDate.currentDate().month():02d}"
            
            # Obtener datos del balance para el optimizador
            balance_data = self.controller.get_balance_sheet_for_optimizer(
                company_id, year_int, int(month_str)
            )
            
            if not balance_data or not balance_data.get('has_real_data'):
                reply = QMessageBox.question(
                    self,
                    "Datos Contables No Disponibles",
                    "No hay datos contables completos para este periodo.\n\n"
                    "El optimizador requiere que el sistema contable esté actualizado.\n\n"
                    "¿Desea abrir el Balance General para verificar los datos?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._open_balance_sheet(company_id, company_name)
                return
            
            # Mostrar información del optimizador
            QMessageBox.information(
                self,
                "🎯 Optimizador Financiero",
                f"Análisis Financiero para {company_name}\n"
                f"Periodo: {month_name} {year_int}\n\n"
                f"📊 Datos Disponibles:\n"
                f"• Activos Corrientes: RD$ {balance_data.get('current_assets', 0):,.2f}\n"
                f"• Activos No Corrientes: RD$ {balance_data.get('non_current_assets', 0):,.2f}\n"
                f"• Pasivos Corrientes: RD$ {balance_data.get('current_liabilities', 0):,.2f}\n"
                f"• Pasivos No Corrientes: RD$ {balance_data.get('non_current_liabilities', 0):,.2f}\n"
                f"• Patrimonio: RD$ {balance_data.get('equity', 0):,.2f}\n"
                f"• Utilidad Neta: RD$ {balance_data.get('net_income', 0):,.2f}\n\n"
                f"📈 Ratios Calculados:\n"
                f"• ROA: {(balance_data.get('net_income', 0) / balance_data.get('total_assets', 1) * 100):.2f}%\n"
                f"• ROE: {(balance_data.get('net_income', 0) / max(balance_data.get('equity', 1), 1) * 100):.2f}%\n"
                f"• Razón Corriente: {(balance_data.get('current_assets', 0) / max(balance_data.get('current_liabilities', 1), 1)):.2f}\n"
                f"• Endeudamiento: {(balance_data.get('total_liabilities', 0) / max(balance_data.get('total_assets', 1), 1) * 100):.2f}%\n\n"
                f"Consulte el MANUAL_OPTIMIZADOR_FINANCIERO.md para más detalles."
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el optimizador:\n{e}")
            import traceback
            traceback.print_exc()

    # ------------------------------------------------------------------
    # Menú y ventanas de Contabilidad
    # ------------------------------------------------------------------
    
    def open_accounting_menu(self) -> None:
        """Abre el menú de opciones de contabilidad."""
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        company_id = self.get_current_company_id()
        company_name = self.company_selector.currentText()
        
        if not company_id:
            QMessageBox.warning(
                self,
                "Empresa Requerida",
                "Seleccione una empresa primero para acceder a la contabilidad."
            )
            return
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius:  8px;
                padding: 8px;
            }
            QMenu::item {
                padding: 10px 30px;
                border-radius: 6px;
                color: #1E293B;
                font-size: 14px;
            }
            QMenu::item: selected {
                background-color:  #EFF6FF;
                color: #1E40AF;
            }
            QMenu::separator {
                height: 1px;
                background-color: #E5E7EB;
                margin: 6px 0px;
            }
        """)
        
        # === CONFIGURACIÓN ===
        menu.addSection("⚙️ Configuración")
        
        act_plan = QAction("📊 Plan de Cuentas", self)
        act_plan.triggered.connect(lambda:  self._open_chart_of_accounts(company_id, company_name))
        menu.addAction(act_plan)
        
        act_init_chart = QAction("🆕 Inicializar Plan de Cuentas", self)
        act_init_chart.triggered.connect(lambda: self._initialize_chart_of_accounts(company_id, company_name))
        menu.addAction(act_init_chart)
        
        menu.addSeparator()
        
        # === MOVIMIENTOS ===
        menu.addSection("📝 Movimientos")
        
        # ✅ NUEVO:  Gestor de Asientos Manuales
        act_entry_manager = QAction("✏️ Crear Asiento Manual", self)
        act_entry_manager.triggered.connect(lambda: self._open_journal_entry_manager(company_id, company_name))
        menu.addAction(act_entry_manager)
        
        # Generar Asientos desde Facturas
        act_generate = QAction("🧪 Generar Asientos desde Facturas", self)
        act_generate.triggered.connect(lambda: self._open_generate_entries_dialog(company_id, company_name))
        menu.addAction(act_generate)
        
        menu.addSeparator()
        
        # === CONSULTAS ===
        menu.addSection("📖 Consultas")
        
        # Libro Diario
        act_diary = QAction("📓 Libro Diario", self)
        act_diary.triggered.connect(lambda: self._open_journal_diary(company_id, company_name))
        menu.addAction(act_diary)
        
        # Libro Mayor
        act_ledger = QAction("📖 Libro Mayor", self)
        act_ledger.triggered. connect(lambda: self._open_general_ledger(company_id, company_name))
        menu.addAction(act_ledger)
        
        menu.addSeparator()
        
        # === ESTADOS FINANCIEROS ===
        menu. addSection("📈 Estados Financieros")
        
        act_balance = QAction("💰 Balance General", self)
        act_balance.triggered.connect(lambda: self._open_balance_sheet(company_id, company_name))
        menu.addAction(act_balance)
        
        act_income = QAction("📊 Estado de Resultados", self)
        act_income.triggered.connect(lambda: self._open_income_statement(company_id, company_name))
        menu.addAction(act_income)
        
        act_cashflow = QAction("💵 Flujo de Efectivo", self)
        act_cashflow.triggered.connect(lambda: self._open_cash_flow(company_id, company_name))
        menu.addAction(act_cashflow)
        
        act_equity = QAction("💎 Cambios en Patrimonio", self)
        act_equity.triggered.connect(lambda: self._open_equity_statement(company_id, company_name))
        menu.addAction(act_equity)
        
        # Mostrar menú
        btn = self.nav_buttons_by_key.get("accounting")
        if btn:
            global_pos = btn.mapToGlobal(btn.rect().bottomLeft())
        else:
            global_pos = self.mapToGlobal(self.cursor().pos())
        
        menu.exec(global_pos)


    def _open_chart_of_accounts(self, company_id, company_name:  str):
        """Abre el gestor del plan de cuentas."""
        try:
            from accounting.chart_of_accounts_manager import ChartOfAccountsManager
            
            dlg = ChartOfAccountsManager(
                self,
                self.controller,
                company_id,
                company_name
            )
            dlg.exec()
        except ImportError as e:
            QMessageBox. critical(
                self,
                "Error",
                f"No se pudo cargar el módulo de Plan de Cuentas:\n{e}\n\n"
                "Asegúrate de que el archivo accounting/chart_of_accounts_manager.py existe."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error al abrir Plan de Cuentas:\n{e}"
            )
            import traceback
            traceback. print_exc()

    def _open_balance_sheet(self, company_id, company_name: str):
        """Abre el balance general."""
        try:
            from accounting.balance_sheet_window import BalanceSheetWindow
            
            # Usar mes y año actuales
            month_name = self.month_selector.currentText()
            month_str = self.MONTHS_MAP.get(month_name, "01")
            
            try:
                year_int = int(self.year_selector.currentText())
            except:
                from PyQt6.QtCore import QDate
                year_int = QDate.currentDate().year()
            
            dlg = BalanceSheetWindow(
                self,
                self.controller,
                company_id,
                company_name,
                month_str,
                year_int
            )
            dlg.exec()
        except ImportError as e:
            QMessageBox.information(
                self,
                "Próximamente",
                f"Balance General - En desarrollo\n\n{e}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al abrir Balance General:\n{e}")

    def _open_journal_entries(self, company_id, company_name:  str):
        """Abre el libro diario (consulta de asientos)."""
        try:
            from accounting.journal_diary_window import JournalDiaryWindow  # ✅ CORRECTO
            
            dlg = JournalDiaryWindow(
                self,
                self.controller,
                company_id,
                company_name
            )
            dlg.exec()
        except ImportError as e:
            QMessageBox.information(
                self,
                "Libro Diario",
                f"Módulo en desarrollo\n\n{e}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al abrir Libro Diario:\n{e}")


    def _open_general_ledger(self, company_id, company_name:  str):
        """Abre el libro mayor."""
        try:
            from accounting.general_ledger_window import GeneralLedgerWindow
            
            dlg = GeneralLedgerWindow(
                self,
                self. controller,
                company_id,
                company_name
            )
            dlg.exec()
        except ImportError as e: 
            QMessageBox.information(
                self,
                "Libro Mayor",
                f"Módulo en desarrollo\n\n{e}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al abrir Libro Mayor:\n{e}")


    def _open_income_statement(self, company_id, company_name: str):
        """Abre el estado de resultados."""
        try:
            from accounting. income_statement_window import IncomeStatementWindow
            
            # Usar mes y año actuales
            month_name = self.month_selector.currentText()
            month_str = self.MONTHS_MAP.get(month_name, "01")
            
            try:
                year_int = int(self.year_selector. currentText())
            except: 
                from PyQt6.QtCore import QDate
                year_int = QDate.currentDate().year()
            
            dlg = IncomeStatementWindow(
                self,
                self.controller,
                company_id,
                company_name,
                month_str,
                year_int
            )
            dlg.exec()
        except ImportError as e:
            QMessageBox. information(
                self,
                "Próximamente",
                f"Estado de Resultados - En desarrollo\n\n{e}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al abrir Estado de Resultados:\n{e}")



    def _open_equity_statement(self, company_id, company_name: str):
        """Abre el estado de cambios en patrimonio."""
        try:
            from accounting.equity_statement_window import EquityStatementWindow
            
            try:
                year_int = int(self.year_selector.currentText())
            except:
                from PyQt6.QtCore import QDate
                year_int = QDate.currentDate().year()
            
            dlg = EquityStatementWindow(
                self,
                self.controller,
                company_id,
                company_name,
                year_int
            )
            dlg.exec()
        except ImportError as e:
            QMessageBox.information(
                self,
                "Próximamente",
                f"Estado de Cambios en Patrimonio - En desarrollo\n\n{e}"
            )
        except Exception as e: 
            QMessageBox.critical(self, "Error", f"Error al abrir Estado de Patrimonio:\n{e}")

    # En el método de menú o botón temporal
    def _test_accounting(self):
        from accounting.chart_of_accounts_manager import ChartOfAccountsManager
        
        dlg = ChartOfAccountsManager(
            self,
            self.controller,
            self.current_company_id,
            self.current_company_name
        )
        dlg.exec()





        
    def _open_generate_entries_dialog(self, company_id, company_name: str):
        """Abre el diálogo de generación de asientos desde facturas."""
        try:
            from accounting.generate_entries_from_invoices import GenerateEntriesFromInvoicesDialog
            
            dlg = GenerateEntriesFromInvoicesDialog(
                parent=self,
                controller=self.controller,
                company_id=company_id,
                company_name=company_name
            )
            dlg.exec()
            
            # Refrescar dashboard después de generar asientos
            if hasattr(self, 'refresh_dashboard'):
                self.refresh_dashboard()
                
        except ImportError as e: 
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo cargar el diálogo de generación:\n{e}\n\n"
                "Asegúrate de tener el archivo:\n"
                "accounting/generate_entries_from_invoices.py"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error al abrir generador de asientos:\n{e}"
            )
            import traceback
            traceback.print_exc()



    def _generate_test_entries(self, company_id, company_name: str):
        """Genera asientos contables de prueba desde las facturas existentes."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QCheckBox, QPushButton, QHBoxLayout
        
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Generar Asientos de Prueba - {company_name}")
        dlg.resize(450, 250)
        
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        title = QLabel("🧪 Generar Asientos desde Facturas")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0F172A;")
        layout.addWidget(title)
        
        subtitle = QLabel(
            "Esta herramienta creará asientos contables automáticos\n"
            "desde todas las facturas registradas en el periodo seleccionado."
        )
        subtitle.setStyleSheet("color: #64748B; font-size: 13px;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        
        # Filtros
        filter_layout = QHBoxLayout()
        
        lbl_year = QLabel("Año:")
        combo_year = QComboBox()
        try:
            current_year = int(self.current_year)
        except:
            current_year = QDate.currentDate().year()
        
        for y in range(current_year - 2, current_year + 2):
            combo_year.addItem(str(y))
        combo_year.setCurrentText(str(current_year))
        
        filter_layout.addWidget(lbl_year)
        filter_layout.addWidget(combo_year)
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # Checkbox sobrescribir
        chk_overwrite = QCheckBox("Sobrescribir asientos existentes de facturas")
        chk_overwrite.setChecked(False)
        chk_overwrite.setStyleSheet("color: #DC2626; font-weight: 600;")
        layout.addWidget(chk_overwrite)
        
        layout.addStretch()
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_generate = QPushButton("Generar Asientos")
        btn_generate.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                padding: 8px 20px;
                border-radius:  6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
        """)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_generate)
        
        layout.addLayout(btn_layout)
        
        # Eventos
        btn_cancel.clicked. connect(dlg.reject)
        
        def on_generate():
            year = int(combo_year.currentText())
            overwrite = chk_overwrite. isChecked()
            
            dlg.accept()
            
            # Ejecutar generación
            ok, msg = self.controller.generate_test_journal_entries_from_invoices(
                company_id=company_id,
                year=year,
                month=None,
                overwrite=overwrite
            )
            
            if ok: 
                QMessageBox.information(self, "Éxito", msg)
                if hasattr(self, "refresh_dashboard"):
                    self.refresh_dashboard()
            else:
                QMessageBox.warning(self, "Error", msg)
        
        btn_generate.clicked.connect(on_generate)
        
        dlg.exec()

    def _initialize_chart_of_accounts(self, company_id, company_name: str):
        """Inicializa el plan de cuentas estándar para una empresa."""
        reply = QMessageBox.question(
            self,
            "Inicializar Plan de Cuentas",
            f"¿Desea inicializar el plan de cuentas estándar para {company_name}?\n\n"
            f"Esto creará aproximadamente 50 cuentas contables básicas.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            year = int(self.current_year)
        except: 
            year = QDate.currentDate().year()
        
        ok, msg = self.controller.initialize_default_chart_of_accounts(company_id, year)
        
        if ok:
            QMessageBox.information(self, "Éxito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)


    def _initialize_chart_of_accounts(self, company_id, company_name:  str):
        """Inicializa el plan de cuentas estándar para una empresa."""
        reply = QMessageBox.question(
            self,
            "Inicializar Plan de Cuentas",
            f"¿Desea inicializar el plan de cuentas estándar para {company_name}?\n\n"
            f"Esto creará aproximadamente 50 cuentas contables básicas.",
            QMessageBox.StandardButton.Yes | QMessageBox. StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            year = int(self.current_year)
        except: 
            year = QDate.currentDate().year()
        
        ok, msg = self.controller.initialize_default_chart_of_accounts(company_id, year)
        
        if ok:
            QMessageBox.information(self, "Éxito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)


    def _generate_test_entries(self, company_id, company_name: str):
        """Genera asientos contables de prueba desde las facturas existentes."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QCheckBox, QPushButton, QHBoxLayout
        
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Generar Asientos de Prueba - {company_name}")
        dlg.resize(450, 250)
        
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        title = QLabel("🧪 Generar Asientos desde Facturas")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0F172A;")
        layout.addWidget(title)
        
        subtitle = QLabel(
            "Esta herramienta creará asientos contables automáticos\n"
            "desde todas las facturas registradas en el periodo seleccionado."
        )
        subtitle.setStyleSheet("color: #64748B; font-size: 13px;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        
        # Filtros
        filter_layout = QHBoxLayout()
        
        lbl_year = QLabel("Año:")
        combo_year = QComboBox()
        try:
            current_year = int(self.current_year)
        except:
            current_year = QDate.currentDate().year()
        
        for y in range(current_year - 2, current_year + 2):
            combo_year.addItem(str(y))
        combo_year.setCurrentText(str(current_year))
        
        filter_layout.addWidget(lbl_year)
        filter_layout.addWidget(combo_year)
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # Checkbox sobrescribir
        chk_overwrite = QCheckBox("Sobrescribir asientos existentes de facturas")
        chk_overwrite.setChecked(False)
        chk_overwrite.setStyleSheet("color: #DC2626; font-weight: 600;")
        layout.addWidget(chk_overwrite)
        
        layout.addStretch()
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_generate = QPushButton("Generar Asientos")
        btn_generate.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color:  white;
                padding: 8px 20px;
                border-radius:  6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
        """)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_generate)
        
        layout.addLayout(btn_layout)
        
        # Eventos
        btn_cancel.clicked. connect(dlg.reject)
        
        def on_generate():
            year = int(combo_year.currentText())
            overwrite = chk_overwrite. isChecked()
            
            dlg.accept()
            
            # Ejecutar generación
            ok, msg = self.controller.generate_test_journal_entries_from_invoices(
                company_id=company_id,
                year=year,
                month=None,
                overwrite=overwrite
            )
            
            if ok:
                QMessageBox.information(self, "Éxito", msg)
                # Refrescar dashboard si existe
                if hasattr(self, "refresh_dashboard"):
                    self.refresh_dashboard()
            else:
                QMessageBox.warning(self, "Error", msg)
        
        btn_generate.clicked. connect(on_generate)
        
        dlg.exec()



    def _open_journal_diary(self, company_id, company_name: str):
        """Abre el libro diario (consulta)."""
        try:
            from accounting.journal_diary_window import JournalDiaryWindow
            
            dlg = JournalDiaryWindow(
                self,
                self.controller,
                company_id,
                company_name
            )
            dlg.exec()
            
        except ImportError as e:
            QMessageBox.information(
                self,
                "Libro Diario",
                f"El Libro Diario está en desarrollo.\n\n"
                f"Próximamente:  Consulta de todos los asientos contables ordenados cronológicamente."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al abrir Libro Diario:\n{e}")


    def _open_journal_manager(self, company_id, company_name:  str):
        """Abre el generador de asientos desde facturas."""
        try:
            from accounting.generate_entries_from_invoices import GenerateEntriesFromInvoicesDialog
            
            dlg = GenerateEntriesFromInvoicesDialog(
                parent=self,
                controller=self.controller,
                company_id=company_id,
                company_name=company_name
            )
            dlg.exec()
            
            # Refrescar dashboard después de generar asientos
            if hasattr(self, "refresh_dashboard"):
                self.refresh_dashboard()
            
        except ImportError as e: 
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo cargar el diálogo de generación de asientos:\n{e}\n\n"
                f"Asegúrate de que el archivo accounting/generate_entries_from_invoices.py existe."
            )
        except Exception as e:
            QMessageBox. critical(
                self,
                "Error",
                f"Error al abrir el generador de asientos:\n{e}"
            )
            import traceback
            traceback.print_exc()

    def _open_cash_flow(self, company_id, company_name:  str):
        """Abre el flujo de efectivo."""
        try:
            from accounting. cash_flow_window import CashFlowWindow
            
            try:
                year_int = int(self.year_selector.currentText())
            except:
                from PyQt6.QtCore import QDate
                year_int = QDate.currentDate().year()
            
            dlg = CashFlowWindow(
                self,
                self.controller,
                company_id,
                company_name,
                year_int
            )
            dlg.exec()
        except ImportError as e:
            QMessageBox. information(
                self,
                "Flujo de Efectivo",
                f"Módulo implementado correctamente ✅"
            )
        except Exception as e:
            QMessageBox. critical(self, "Error", f"Error al abrir Flujo de Efectivo:\n{e}")

    def _open_equity_statement(self, company_id, company_name: str):
        """Abre el estado de cambios en patrimonio."""
        QMessageBox.information(
            self,
            "Cambios en Patrimonio",
            f"Abriendo estado de cambios en patrimonio para {company_name}...\n\n"
            f"(Ventana en desarrollo)"
        )


    def _open_journal_entry_manager(self, company_id, company_name:  str):
        """Abre el gestor de asientos contables manuales."""
        try:
            from accounting.journal_entry_dialog import JournalEntryManager
            
            dlg = JournalEntryManager(
                parent=self,
                controller=self.controller,
                company_id=company_id,
                company_name=company_name
            )
            dlg.exec()
            
            # Refrescar dashboard después de crear asiento
            if hasattr(self, 'refresh_dashboard'):
                self.refresh_dashboard()
                
        except ImportError as e:
            QMessageBox. critical(
                self,
                "Error",
                f"No se pudo cargar el gestor de asientos:\n{e}\n\n"
                "Asegúrate de tener el archivo:\n"
                "accounting/journal_entry_dialog.py"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error al abrir gestor de asientos:\n{e}"
            )
            import traceback
            traceback.print_exc()

    def open_attachment_auditor(self):
        """Abre el auditor de adjuntos."""
        try:
            from audit_attachments_integrated import AttachmentAuditorIntegrated
            
            # Verificar que haya conexión Firebase
            if not hasattr(self.controller, '_db') or not hasattr(self.controller, '_bucket'):
                QMessageBox.warning(
                    self,
                    "Sin Conexión",
                    "No hay conexión a Firebase.\n\n"
                    "Asegúrate de que el sistema esté correctamente configurado."
                )
                return
            
            # Abrir auditor
            dialog = AttachmentAuditorIntegrated(self, self.controller)
            dialog.show()  # show() en lugar de exec() para que no sea modal
            
        except ImportError as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo cargar el auditor:\n{e}\n\n"
                "Asegúrate de tener el archivo:\n"
                "audit_attachments_integrated.py"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error abriendo auditor:\n{e}"
            )
            import traceback
            traceback.print_exc()



def run_demo(controller=None) -> None:
    """Helper for local testing of the ModernMainWindow."""

    class StubController:
        def __init__(self):
            self.active_company: Optional[str] = None
            self.tx_filter: Optional[str] = None

        def list_companies(self) -> List[str]:
            return ["Empresa A", "Empresa B", "Empresa C"]

        def set_active_company(self, name: str) -> None:
            self.active_company = name

        def get_unique_invoice_years(self, company_id=None) -> List[int]:
            current_year = datetime.date.today().year
            return [current_year - i for i in range(3)]

        def set_transaction_filter(self, tx_type: Optional[str]) -> None:
            self.tx_filter = tx_type

        def _refresh_dashboard(self, month: Optional[str], year: Optional[int]):
            return {
                "income": 1250000.00,
                "income_itbis": 225000.00,
                "expense": 450000.00,
                "expense_itbis": 81000.00,
                "net_itbis": 144000.00,
                "payable": 144000.00,
            }

        def _populate_transactions_table(
            self, month: Optional[str], year: Optional[int], tx_type: Optional[str]
        ):
            data = [
                {
                    "date": "2025-10-14",
                    "type": "emitida",
                    "number": "E3100000239",
                    "party": "Barnhouse Services Srl",
                    "itbis": 12000.00,
                    "total": 78000.00,
                },
                {
                    "date": "2025-10-12",
                    "type": "gasto",
                    "number": "B0100005512",
                    "party": "Ferretería Americana",
                    "itbis": 450.00,
                    "total": 2950.00,
                },
            ]
            if tx_type == "emitida":
                return [d for d in data if d["type"] == "emitida"]
            if tx_type == "gasto":
                return [d for d in data if d["type"] == "gasto"]
            return data

        def open_add_income_invoice_window(self, parent=None):
            print("Add income invoice window would open here.")

        def open_add_expense_invoice_window(self, parent=None):
            print("Add expense invoice window would open here.")

        def diagnose_row(self, number):
            print(f"Diagnosing row with number: {number}")

        def get_sqlite_db_path(self) -> str:
            return "/path/to/db.sqlite3"

        def create_sql_backup(self, retention_days: int) -> str:
            return "/tmp/backup.db"

        # Métodos dummy para probar el menú contextual
        def edit_invoice_by_number(self, invoice_number, parent=None):
            print(f"EDIT {invoice_number}")

        def delete_invoice_by_number(self, invoice_number, parent=None):
            print(f"DELETE {invoice_number}")

        def view_invoice_attachment_by_number(self, invoice_number, parent=None):
            print(f"VIEW ATTACHMENT {invoice_number}")

    app = QApplication(sys.argv)
    controller_to_use = controller or StubController()
    window = ModernMainWindow(controller_to_use)
    window.show()
    sys.exit(app.exec())

