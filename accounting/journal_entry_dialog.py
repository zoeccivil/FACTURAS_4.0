from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QLineEdit,
    QDateEdit,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QTextEdit,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QDoubleValidator
import datetime


class JournalEntryManager(QDialog):
    """
    Gestor de Asientos Contables. 
    
    Permite: 
    - Crear nuevos asientos contables
    - Ver lista de asientos existentes
    - Validar partida doble (Débito = Crédito)
    - Búsqueda y filtros
    """

    def __init__(self, parent, controller, company_id, company_name:  str):
        super().__init__(parent)
        self.controller = controller
        self.company_id = company_id
        self.company_name = company_name

        self.setWindowTitle(f"Asientos Contables - {company_name}")
        self.resize(1200, 700)
        self.setModal(True)

        self._build_ui()
        self._load_entries()

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

        title = QLabel("📝 Asientos Contables")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A;")
        title_row.addWidget(title)
        title_row.addStretch()

        # Botones
        self.btn_new = QPushButton("➕ Nuevo Asiento")
        self.btn_new.setObjectName("primaryButton")
        self.btn_new.clicked.connect(self._new_entry)

        self.btn_refresh = QPushButton("🔃 Refrescar")
        self.btn_refresh.setObjectName("refreshButton")
        self.btn_refresh.clicked.connect(self._load_entries)

        title_row.addWidget(self.btn_new)
        title_row.addWidget(self.btn_refresh)

        header_layout.addLayout(title_row)

        subtitle = QLabel(f"{self.company_name}")
        subtitle.setStyleSheet("font-size: 12px; color: #64748B;")
        header_layout.addWidget(subtitle)

        root.addWidget(header_card)

        # === BÚSQUEDA ===
        search_row = QHBoxLayout()
        search_row.setSpacing(12)

        lbl_search = QLabel("🔍 Buscar:")
        lbl_search.setStyleSheet("font-weight: 600; color: #475569;")
        search_row.addWidget(lbl_search)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("modernInput")
        self.search_input.setPlaceholderText("Buscar por referencia o descripción...")
        search_row.addWidget(self.search_input, 1)

        root.addLayout(search_row)

        # === TABLA DE ASIENTOS ===
        self.table = QTableWidget()
        self.table.setObjectName("entriesTable")
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Fecha", "Referencia", "Descripción", "Débito", "Crédito", "Estado"
        ])

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
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.doubleClicked.connect(self._on_entry_double_click)

        root.addWidget(self.table)

        # === ESTADÍSTICAS ===
        stats_card = QFrame()
        stats_card.setObjectName("statsCard")
        stats_layout = QHBoxLayout(stats_card)
        stats_layout.setContentsMargins(20, 12, 20, 12)
        stats_layout.setSpacing(20)

        self.lbl_total = QLabel("Total:  0 asientos")
        self.lbl_total.setStyleSheet("font-weight: 600; color: #1E293B;")
        stats_layout.addWidget(self.lbl_total)

        stats_layout.addStretch()

        root.addWidget(stats_card)

        # === ESTILOS ===
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }

            QFrame#headerCard, QFrame#statsCard {
                background-color:  #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }

            QLineEdit#modernInput {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px 12px;
                color: #0F172A;
                font-size: 13px;
            }

            QLineEdit#modernInput:focus {
                border-color: #3B82F6;
                border-width: 2px;
            }

            QPushButton#primaryButton {
                background-color: #15803D;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0px 20px;
                font-weight: 600;
                font-size: 14px;
                min-width: 150px;
                height: 36px;
            }
            QPushButton#primaryButton:hover { background-color: #166534; }

            QPushButton#refreshButton {
                background-color: #64748B;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0px 16px;
                font-weight:  600;
                font-size: 14px;
                height: 36px;
            }
            QPushButton#refreshButton:hover { background-color: #475569; }

            QTableWidget#entriesTable {
                background-color: #FFFFFF;
                alternate-background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                color: #0F172A;
                font-size: 13px;
            }

            QTableWidget#entriesTable::item {
                padding: 6px;
            }

            QTableWidget#entriesTable::item:selected {
                background-color: #EFF6FF;
                color: #1E293B;
            }

            QHeaderView::section {
                background-color: #F1F5F9;
                border: none;
                padding: 10px 8px;
                color: #475569;
                font-weight:  700;
                font-size: 12px;
            }

            /* === ARREGLO PARA QMESSAGEBOX === */
            QMessageBox {
                background-color:  #FFFFFF;
            }
            QMessageBox QLabel {
                color: #0F172A;
                font-size: 13px;
                background-color: transparent;
                min-width: 300px;
            }
            QMessageBox QPushButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 600;
                font-size: 13px;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #2563EB;
            }
        """)

    def _load_entries(self):
        """Carga la lista de asientos contables."""
        self.table. setRowCount(0)

        try:
            if not hasattr(self.  controller, "get_journal_entries"):
                QMessageBox.information(
                    self,
                    "Asientos Contables",
                    "Método get_journal_entries no implementado."
                )
                return

            # Obtener asientos
            entries = self.controller.get_journal_entries(self.company_id, limit=100) or []

            if not entries:
                self.lbl_total. setText("Total:   0 asientos")
                return

            # Poblar tabla
            self.table.setRowCount(len(entries))

            for row, entry in enumerate(entries):
                # Fecha
                entry_date = entry.get("entry_date")
                if hasattr(entry_date, "strftime"):
                    date_str = entry_date.strftime("%d/%m/%Y")
                else:
                    date_str = str(entry_date) if entry_date else ""

                item_date = QTableWidgetItem(date_str)
                self.table.setItem(row, 0, item_date)

                # Referencia
                reference = entry.get("reference", "")
                item_ref = QTableWidgetItem(reference)
                self.table.  setItem(row, 1, item_ref)

                # Descripción
                description = entry.get("description", "")
                item_desc = QTableWidgetItem(description)
                self.table.setItem(row, 2, item_desc)

                # Débito
                total_debit = float(entry.get("total_debit", 0))
                item_debit = QTableWidgetItem(f"RD$ {total_debit:,.2f}")
                item_debit.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item_debit.setForeground(QColor("#15803D"))
                self.table.setItem(row, 3, item_debit)

                # Crédito
                total_credit = float(entry.get("total_credit", 0))
                item_credit = QTableWidgetItem(f"RD$ {total_credit:,.2f}")
                item_credit. setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item_credit.setForeground(QColor("#DC2626"))
                self.table. setItem(row, 4, item_credit)

                # Estado
                status = entry.get("status", "")
                status_text = "✅ Publicado" if status == "POSTED" else status
                item_status = QTableWidgetItem(status_text)
                self.table.setItem(row, 5, item_status)

            self.lbl_total.setText(f"Total: {len(entries)} asientos")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando asientos:\n{e}")
            import traceback
            traceback. print_exc()

    def _new_entry(self):
        """Abre diálogo para crear nuevo asiento."""
        dlg = JournalEntryFormDialog(self, self.controller, self.company_id, self.company_name)
        if dlg.exec():
            self._load_entries()

    def _on_entry_double_click(self, index):
        """Maneja doble click en un asiento."""
        # TODO: Abrir para ver/editar
        QMessageBox.information(self, "Ver Asiento", "Funcionalidad de edición en desarrollo.")


class JournalEntryFormDialog(QDialog):
    """Formulario para crear/editar asientos contables."""

    def __init__(self, parent, controller, company_id, company_name: str, entry=None):
        super().__init__(parent)
        self.controller = controller
        self.company_id = company_id
        self.company_name = company_name
        self.entry = entry
        self.is_edit = entry is not None

        self.accounts = []  # Lista de cuentas disponibles
        self.lines = []  # Líneas del asiento

        title = "Editar Asiento" if self.is_edit else "Nuevo Asiento Contable"
        self.setWindowTitle(title)
        self.resize(900, 650)
        self.setModal(True)

        self._load_accounts()
        self._build_ui()

    def _load_accounts(self):
        """Carga las cuentas disponibles."""
        try:
            if hasattr(self.controller, "get_chart_of_accounts"):
                all_accounts = self.controller.get_chart_of_accounts(self.company_id) or []
                # Filtrar solo cuentas detalle
                self.accounts = [a for a in all_accounts if a.get("is_detail", False)]
        except Exception as e:
            print(f"[JOURNAL_ENTRY] Error cargando cuentas: {e}")
            self.accounts = []

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # === HEADER ===
        title = QLabel("📝 " + ("Editar Asiento" if self.is_edit else "Nuevo Asiento Contable"))
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0F172A;")
        root.addWidget(title)

        subtitle = QLabel(f"{self.company_name}")
        subtitle.setStyleSheet("font-size:  12px; color: #64748B;")
        root.addWidget(subtitle)

        # === DATOS GENERALES ===
        general_frame = QFrame()
        general_frame.setObjectName("generalFrame")
        general_layout = QVBoxLayout(general_frame)
        general_layout.setContentsMargins(16, 16, 16, 16)
        general_layout.setSpacing(12)

        # Fecha y Referencia
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        lbl_date = QLabel("Fecha: *")
        lbl_date.setStyleSheet("font-weight:  600; color: #475569;")
        row1.addWidget(lbl_date)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        row1.addWidget(self.date_edit)

        lbl_ref = QLabel("Referencia:")
        lbl_ref.setStyleSheet("font-weight: 600; color: #475569;")
        row1.addWidget(lbl_ref)

        self.ref_edit = QLineEdit()
        self.ref_edit.setPlaceholderText("Ej: FAC-2025-001")
        row1.addWidget(self.ref_edit, 1)

        general_layout.addLayout(row1)

        # Descripción
        lbl_desc = QLabel("Descripción:*")
        lbl_desc.setStyleSheet("font-weight: 600; color: #475569;")
        general_layout.addWidget(lbl_desc)

        self.desc_edit = QTextEdit()
        self.desc_edit.setObjectName("modernTextEdit")
        self.desc_edit.setPlaceholderText("Descripción del asiento contable...")
        self.desc_edit.setMaximumHeight(60)
        general_layout.addWidget(self.desc_edit)

        root.addWidget(general_frame)

        # === LÍNEAS DEL ASIENTO ===
        lines_label = QLabel("Líneas del Asiento (Partida Doble):")
        lines_label.setStyleSheet("font-weight: 700; color: #1E293B; font-size: 14px;")
        root.addWidget(lines_label)

        self.lines_table = QTableWidget()
        self.lines_table.setObjectName("linesTable")
        self.lines_table.setColumnCount(4)
        self.lines_table.setHorizontalHeaderLabels([
            "Cuenta", "Descripción", "Débito", "Crédito"
        ])

        header = self.lines_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.lines_table.setMinimumHeight(200)
        root.addWidget(self.lines_table)

        # Botón agregar línea
        btn_add_line = QPushButton("➕ Agregar Línea")
        btn_add_line.setObjectName("secondaryButton")
        btn_add_line.clicked.connect(self._add_line)
        root.addWidget(btn_add_line)

        # === TOTALES ===
        totals_frame = QFrame()
        totals_frame.setObjectName("totalsFrame")
        totals_layout = QHBoxLayout(totals_frame)
        totals_layout.setContentsMargins(16, 12, 16, 12)
        totals_layout.setSpacing(20)

        totals_layout.addStretch()

        lbl_debit = QLabel("TOTAL DÉBITO:")
        lbl_debit.setStyleSheet("font-weight: 700; color: #15803D; font-size: 14px;")
        totals_layout.addWidget(lbl_debit)

        self.total_debit_label = QLabel("RD$ 0.00")
        self.total_debit_label.setStyleSheet("font-weight:  800; color: #15803D; font-size: 16px;")
        totals_layout.addWidget(self.total_debit_label)

        totals_layout.addSpacing(20)

        lbl_credit = QLabel("TOTAL CRÉDITO:")
        lbl_credit.setStyleSheet("font-weight: 700; color: #DC2626; font-size: 14px;")
        totals_layout.addWidget(lbl_credit)

        self.total_credit_label = QLabel("RD$ 0.00")
        self.total_credit_label.setStyleSheet("font-weight: 800; color: #DC2626; font-size:  16px;")
        totals_layout.addWidget(self.total_credit_label)

        totals_layout.addSpacing(20)

        self.balance_status = QLabel("⏳ Sin líneas")
        self.balance_status.setStyleSheet("font-weight: 700; color: #64748B; font-size: 14px;")
        totals_layout.addWidget(self.balance_status)

        root.addWidget(totals_frame)

        # === BOTONES ===
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        btn_cancel = QPushButton("❌ Cancelar")
        btn_cancel.setObjectName("cancelButton")
        btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("💾 Guardar Asiento")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.clicked.connect(self._save_entry)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_save)

        root.addLayout(btn_layout)

        # === ESTILOS ===
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }

            QFrame#generalFrame, QFrame#totalsFrame {
                background-color: #FFFFFF;
                border-radius: 8px;
                border: 1px solid #E5E7EB;
            }

            QFrame#totalsFrame {
                border: 2px solid #3B82F6;
                background:  qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #EFF6FF,
                    stop:1 #FFFFFF
                );
            }

            QLabel {
                color: #0F172A;
            }

            QLineEdit, QTextEdit#modernTextEdit, QDateEdit {
                padding: 8px 12px;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                background-color: #FFFFFF;
                color: #0F172A;
                font-size: 13px;
            }

            QLineEdit:focus, QTextEdit#modernTextEdit:focus, QDateEdit:focus {
                border-color: #3B82F6;
                border-width: 2px;
            }

            QTableWidget#linesTable {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                color: #0F172A;
            }

            QHeaderView::section {
                background-color: #F1F5F9;
                border: none;
                padding: 8px;
                color: #475569;
                font-weight: 700;
                font-size: 12px;
            }

            QPushButton#primaryButton {
                background-color:  #15803D;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-weight: 600;
                font-size: 14px;
                min-width: 150px;
            }
            QPushButton#primaryButton:hover { background-color: #166534; }

            QPushButton#secondaryButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 20px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton#secondaryButton:hover { background-color: #2563EB; }

            QPushButton#cancelButton {
                background-color: #DC2626;
                color:  #FFFFFF;
                border:  none;
                border-radius:  8px;
                padding:  10px 24px;
                font-weight: 600;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton#cancelButton:hover { background-color: #B91C1C; }

            /* === ARREGLO PARA QMESSAGEBOX === */
            QMessageBox {
                background-color:  #FFFFFF;
            }
            QMessageBox QLabel {
                color: #0F172A;
                font-size: 13px;
                background-color: transparent;
                min-width: 300px;
            }
            QMessageBox QPushButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 600;
                font-size: 13px;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #2563EB;
            }
        """)

    def _add_line(self):
        """Agrega una nueva línea al asiento."""
        if not self.accounts:
            QMessageBox.warning(
                self,
                "Sin Cuentas",
                "No hay cuentas disponibles.\n\nInicializa el plan de cuentas primero."
            )
            return

        row = self.lines_table.rowCount()
        self.lines_table.insertRow(row)

        # ComboBox de cuentas
        combo_account = QComboBox()
        combo_account.addItem("-- Seleccionar Cuenta --", None)
        for acc in self.accounts:
            code = acc.get("account_code", "")
            name = acc.get("account_name", "")
            combo_account.addItem(f"{code} - {name}", acc)
        self.lines_table.setCellWidget(row, 0, combo_account)

        # Descripción
        edit_desc = QLineEdit()
        edit_desc.setPlaceholderText("Descripción de la línea...")
        self.lines_table.setCellWidget(row, 1, edit_desc)

        # Débito
        edit_debit = QLineEdit()
        edit_debit.setPlaceholderText("0.00")
        edit_debit.setAlignment(Qt.AlignmentFlag.AlignRight)
        validator_debit = QDoubleValidator(0.0, 999999999.99, 2)
        edit_debit.setValidator(validator_debit)
        edit_debit.textChanged.connect(self._update_totals)
        self.lines_table.setCellWidget(row, 2, edit_debit)

        # Crédito
        edit_credit = QLineEdit()
        edit_credit.setPlaceholderText("0.00")
        edit_credit.setAlignment(Qt.AlignmentFlag.AlignRight)
        validator_credit = QDoubleValidator(0.0, 999999999.99, 2)
        edit_credit.setValidator(validator_credit)
        edit_credit.textChanged.connect(self._update_totals)
        self.lines_table.setCellWidget(row, 3, edit_credit)

        self._update_totals()

    def _update_totals(self):
        """Actualiza los totales de débito y crédito."""
        total_debit = 0.0
        total_credit = 0.0

        for row in range(self.lines_table.rowCount()):
            # Débito
            debit_widget = self.lines_table.cellWidget(row, 2)
            if debit_widget: 
                debit_text = debit_widget.text().strip().replace(",", "")
                try:
                    total_debit += float(debit_text) if debit_text else 0.0
                except ValueError:
                    pass

            # Crédito
            credit_widget = self.lines_table.cellWidget(row, 3)
            if credit_widget:
                credit_text = credit_widget.text().strip().replace(",", "")
                try:
                    total_credit += float(credit_text) if credit_text else 0.0
                except ValueError:
                    pass

        self.total_debit_label.setText(f"RD$ {total_debit: ,.2f}")
        self.total_credit_label.setText(f"RD$ {total_credit:,.2f}")

        # Verificar balance
        difference = abs(total_debit - total_credit)

        if self.lines_table.rowCount() == 0:
            self.balance_status.setText("⏳ Sin líneas")
            self.balance_status.setStyleSheet("font-weight: 700; color: #64748B; font-size: 14px;")
        elif difference < 0.01:
            self.balance_status.setText("✅ CUADRADO")
            self.balance_status.setStyleSheet("font-weight: 700; color: #15803D; font-size: 14px;")
        else:
            self.balance_status.setText(f"⚠️ DESCUADRE:  RD$ {difference:,.2f}")
            self.balance_status.setStyleSheet("font-weight: 700; color: #DC2626; font-size: 14px;")

    def _save_entry(self):
        """Guarda el asiento contable."""
        # ========================================
        # VALIDACIÓN 1: Descripción (CORREGIDA)
        # ========================================
        description = ""
        if hasattr(self, 'desc_edit') and self.desc_edit is not None:
            try:
                description = self.desc_edit.toPlainText().strip()
            except Exception as e:
                print(f"[JOURNAL_ENTRY] Error leyendo descripción: {e}")
                description = ""
        
        # ✅ CORRECCIÓN: Si está vacía, usar referencia o fecha como fallback
        reference = self.ref_edit.text().strip()
        
        if not description:
            if reference:
                description = f"Asiento {reference}"
            else:
                entry_date = self.date_edit.date().toPyDate()
                description = f"Asiento contable del {entry_date. strftime('%d/%m/%Y')}"
        
        print(f"[JOURNAL_ENTRY] Descripción final: '{description}'")

        # ========================================
        # VALIDACIÓN 2: Mínimo 2 líneas
        # ========================================
        if self.lines_table.rowCount() < 2:
            QMessageBox.warning(
                self,
                "Validación",
                "El asiento debe tener al menos 2 líneas (partida doble)."
            )
            return

        # ========================================
        # RECOLECCIÓN Y VALIDACIÓN DE LÍNEAS
        # ========================================
        lines = []
        total_debit = 0.0
        total_credit = 0.0

        for row in range(self. lines_table.rowCount()):
            # Cuenta
            combo_account = self.lines_table.cellWidget(row, 0)
            if not combo_account or combo_account.currentIndex() == 0:
                QMessageBox.warning(
                    self,
                    "Validación",
                    f"La línea {row + 1} no tiene cuenta seleccionada."
                )
                return
            
            account = combo_account.currentData()
            account_id = account.get("account_code", "")
            account_name = account.get("account_name", "")

            # Descripción de línea
            desc_widget = self.lines_table.cellWidget(row, 1)
            line_desc = desc_widget.text().strip() if desc_widget else ""

            # Débito
            debit_widget = self. lines_table.cellWidget(row, 2)
            debit = 0.0
            if debit_widget: 
                try:
                    debit_text = debit_widget. text().strip().replace(",", "")
                    debit = float(debit_text) if debit_text else 0.0
                except ValueError:
                    pass

            # Crédito
            credit_widget = self.lines_table.cellWidget(row, 3)
            credit = 0.0
            if credit_widget:
                try:
                    credit_text = credit_widget.text().strip().replace(",", "")
                    credit = float(credit_text) if credit_text else 0.0
                except ValueError:
                    pass

            # Validar que tenga débito O crédito (no ambos)
            if debit > 0 and credit > 0:
                QMessageBox.warning(
                    self,
                    "Validación",
                    f"La línea {row + 1} tiene débito Y crédito.\n"
                    "Cada línea debe tener solo débito O crédito."
                )
                return

            if debit == 0 and credit == 0:
                QMessageBox.warning(
                    self,
                    "Validación",
                    f"La línea {row + 1} no tiene monto (débito o crédito)."
                )
                return

            total_debit += debit
            total_credit += credit

            lines.append({
                "account_id": account_id,
                "account_name": account_name,
                "debit":  debit,
                "credit":  credit,
                "description": line_desc or description,
            })

        # ========================================
        # VALIDACIÓN 3: Balance de partida doble
        # ========================================
        if abs(total_debit - total_credit) >= 0.01:
            QMessageBox.warning(
                self,
                "Balance No Cuadrado",
                f"El asiento no cuadra:\n\n"
                f"Débito: RD$ {total_debit:,.2f}\n"
                f"Crédito: RD$ {total_credit:,.2f}\n"
                f"Diferencia:  RD$ {abs(total_debit - total_credit):,.2f}\n\n"
                f"Débito debe ser igual a Crédito."
            )
            return

        # ========================================
        # GUARDAR EN FIREBASE
        # ========================================
        entry_date = self.date_edit.date().toPyDate()

        try:
            if hasattr(self.controller, "create_journal_entry"):
                ok, msg = self.controller.create_journal_entry(
                    self. company_id,
                    entry_date,
                    reference,
                    description,
                    lines
                )

                if ok:
                    QMessageBox.information(
                        self,
                        "Éxito",
                        f"{msg}\n\n"
                        f"Débito: RD$ {total_debit: ,.2f}\n"
                        f"Crédito:  RD$ {total_credit: ,.2f}"
                    )
                    self.accept()
                else:
                    QMessageBox.warning(self, "Error", msg)
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Método create_journal_entry no implementado en el controller."
                )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar asiento:\n{e}")
            import traceback
            traceback.print_exc()