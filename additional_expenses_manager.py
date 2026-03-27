from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QComboBox,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QDateEdit,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
import datetime
import calendar


class AdditionalExpensesManager(QDialog):
    """
    Ventana para gestionar gastos adicionales (no facturados). 
    """

    MONTHS_MAP = {
        "Enero":  "01", "Febrero": "02", "Marzo": "03", "Abril": "04",
        "Mayo": "05", "Junio": "06", "Julio":  "07", "Agosto": "08",
        "Septiembre": "09", "Octubre": "10", "Noviembre": "11", "Diciembre": "12",
    }

    def __init__(
        self,
        parent,
        controller,
        company_id,
        company_name:  str,
        month_str: str,
        year_int: int,
    ):
        super().__init__(parent)
        self.controller = controller
        self.company_id = company_id
        self. company_name = company_name
        self.current_month_str = month_str
        self.current_year_int = year_int
        
        self.editing_expense_id = None

        self.setWindowTitle(f"Gastos Adicionales - {company_name}")
        self.resize(950, 640)
        self.setModal(True)

        self._build_ui()
        self._load_expenses()

    def _get_last_day_of_month(self):
        """Devuelve el último día del mes actual del periodo."""
        try:
            year = self.current_year_int
            month = int(self.current_month_str)
            last_day = calendar.monthrange(year, month)[1]
            return QDate(year, month, last_day)
        except:
            return QDate.currentDate()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        header_card = QFrame()
        header_card.setObjectName("headerCard")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(4)

        header = QLabel(f"📝 Gastos Adicionales")
        header.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A;")
        
        month_name = [k for k, v in self. MONTHS_MAP.items() if v == self.current_month_str][0]
        period_lbl = QLabel(f"{self.company_name} – {month_name} {self. current_year_int}")
        period_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        
        header_layout.addWidget(header)
        header_layout.addWidget(period_lbl)
        
        root.addWidget(header_card)

        form_card = QFrame()
        form_card.setObjectName("formCard")
        form_layout = QVBoxLayout(form_card)
        form_layout. setContentsMargins(20, 16, 20, 16)
        form_layout.setSpacing(12)

        form_title = QLabel("Agregar/Editar Gasto")
        form_title.setStyleSheet("font-weight: 700; color: #1E293B; font-size: 14px;")
        form_layout.addWidget(form_title)

        row1 = QHBoxLayout()
        row1.setSpacing(12)

        lbl_concepto = QLabel("Concepto:")
        lbl_concepto.setStyleSheet("color: #475569; font-weight: 600;")
        row1.addWidget(lbl_concepto)
        
        self.edit_concepto = QLineEdit()
        self.edit_concepto.setPlaceholderText("Ej: Nómina, Servicios, Alquiler...")
        self.edit_concepto.setObjectName("modernInput")
        row1.addWidget(self.edit_concepto, 2)

        lbl_monto = QLabel("Monto:")
        lbl_monto. setStyleSheet("color: #475569; font-weight: 600;")
        row1.addWidget(lbl_monto)
        
        self.edit_monto = QLineEdit()
        self.edit_monto. setPlaceholderText("0.00")
        self.edit_monto.setObjectName("modernInput")
        self.edit_monto.setMaximumWidth(150)
        self.edit_monto.setAlignment(Qt.AlignmentFlag. AlignRight)
        row1.addWidget(self.edit_monto)

        form_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(12)

        lbl_fecha = QLabel("Fecha:")
        lbl_fecha.setStyleSheet("color: #475569; font-weight: 600;")
        row2.addWidget(lbl_fecha)
        
        self.date_picker = QDateEdit()
        self.date_picker.setObjectName("modernDateEdit")
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDate(self._get_last_day_of_month())
        self.date_picker.setDisplayFormat("dd/MM/yyyy")
        self.date_picker.setMinimumWidth(140)
        row2.addWidget(self.date_picker)

        lbl_categoria = QLabel("Categoría:")
        lbl_categoria.setStyleSheet("color: #475569; font-weight:  600;")
        row2.addWidget(lbl_categoria)
        
        self.combo_categoria = QComboBox()
        self.combo_categoria. setObjectName("modernCombo")
        self.combo_categoria.addItems([
            "Nómina",
            "Servicios",
            "Alquiler",
            "Mantenimiento",
            "Publicidad",
            "Transporte",
            "Depreciación",
            "Otros"
        ])
        self.combo_categoria.setEditable(True)
        self.combo_categoria.setMinimumWidth(160)
        row2.addWidget(self.combo_categoria, 1)

        form_layout.addLayout(row2)

        row3 = QVBoxLayout()
        row3.setSpacing(4)
        
        lbl_notas = QLabel("Notas:")
        lbl_notas.setStyleSheet("color: #475569; font-weight: 600;")
        row3.addWidget(lbl_notas)
        
        self.edit_notas = QTextEdit()
        self.edit_notas.setObjectName("modernTextEdit")
        self.edit_notas.setPlaceholderText("Información adicional (opcional)...")
        self.edit_notas.setMaximumHeight(60)
        row3.addWidget(self.edit_notas)

        form_layout.addLayout(row3)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_guardar = QPushButton("💾 Guardar")
        self.btn_guardar.setObjectName("primaryButton")
        self.btn_guardar.clicked.connect(self._save_expense)
        self.btn_guardar.setMinimumHeight(38)

        self.btn_cancelar = QPushButton("❌ Cancelar")
        self.btn_cancelar.setObjectName("secondaryButton")
        self.btn_cancelar. clicked.connect(self._cancel_edit)
        self.btn_cancelar.setVisible(False)
        self.btn_cancelar.setMinimumHeight(38)

        btn_row.addWidget(self.btn_guardar)
        btn_row.addWidget(self.btn_cancelar)
        btn_row.addStretch()

        form_layout.addLayout(btn_row)
        root.addWidget(form_card)

        table_label = QLabel("📋 Gastos registrados:")
        table_label.setStyleSheet("font-weight: 700; color: #1E293B; font-size:  14px; margin-top: 8px;")
        root.addWidget(table_label)

        self.table = QTableWidget()
        self.table.setObjectName("modernTable")
        self.table. setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Fecha", "Concepto", "Monto", "Categoría", "Notas", "Acciones"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode. ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView. ResizeMode. Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 120)
        
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget. SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget. EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(40)

        root.addWidget(self.table)

        total_card = QFrame()
        total_card.setObjectName("totalCard")
        total_layout = QHBoxLayout(total_card)
        total_layout.setContentsMargins(20, 16, 20, 16)
        total_layout. setSpacing(12)
        
        total_lbl = QLabel("TOTAL GASTOS ADICIONALES:")
        total_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #1E293B;")
        
        self.label_total = QLabel("RD$ 0.00")
        self.label_total.setStyleSheet(
            "font-size: 20px; font-weight: 800; color: #DC2626;"
        )
        
        total_layout.addStretch()
        total_layout. addWidget(total_lbl)
        total_layout.addWidget(self.label_total)
        
        root.addWidget(total_card)

        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }
            
            QFrame#headerCard {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }
            
            QFrame#formCard {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }
            
            QFrame#totalCard {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 2px solid #DC2626;
                background:  qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FEF2F2, 
                    stop:1 #FFFFFF
                );
            }
            
            QLineEdit#modernInput {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px 12px;
                color: #0F172A;
                font-size: 13px;
            }
            
            QLineEdit#modernInput: focus {
                border-color: #3B82F6;
                border-width: 2px;
            }
            
            QLineEdit#modernInput:: placeholder {
                color: #94A3B8;
            }
            
            QTextEdit#modernTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px;
                color: #0F172A;
                font-size:  13px;
            }
            
            QTextEdit#modernTextEdit:focus {
                border-color: #3B82F6;
                border-width:  2px;
            }
            
            QComboBox#modernCombo {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px 12px;
                color: #0F172A;
                font-size: 13px;
                font-weight: 500;
            }
            
            QComboBox#modernCombo:hover {
                border-color: #3B82F6;
            }
            
            QComboBox#modernCombo:focus {
                border-color: #2563EB;
                border-width: 2px;
            }
            
            QComboBox#modernCombo:: drop-down {
                border: none;
                width: 30px;
            }
            
            QComboBox#modernCombo::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #64748B;
                margin-right: 8px;
            }
            
            QComboBox#modernCombo QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                selection-background-color: #EFF6FF;
                selection-color: #1E293B;
                padding:  4px;
                color: #0F172A;
                font-size: 13px;
            }
            
            QDateEdit#modernDateEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px 12px;
                color: #0F172A;
                font-size: 13px;
                font-weight: 500;
            }
            
            QDateEdit#modernDateEdit:hover {
                border-color: #3B82F6;
            }
            
            QDateEdit#modernDateEdit:focus {
                border-color: #2563EB;
                border-width: 2px;
            }
            
            QDateEdit#modernDateEdit::drop-down {
                border: none;
                width: 30px;
            }
            
            QDateEdit#modernDateEdit:: down-arrow {
                image:  none;
                border-left:  4px solid transparent;
                border-right: 4px solid transparent;
                border-top:  6px solid #64748B;
                margin-right: 8px;
            }
            
            QDateEdit#modernDateEdit QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                selection-background-color: #EFF6FF;
                selection-color: #1E293B;
                color: #0F172A;
            }
            
            QPushButton#primaryButton {
                background-color: #15803D;
                color: #FFFFFF;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight:  600;
                font-size: 14px;
                border: none;
                min-width: 120px;
            }
            
            QPushButton#primaryButton: hover {
                background-color:  #166534;
            }
            
            QPushButton#primaryButton: pressed {
                background-color:  #14532D;
            }
            
            QPushButton#secondaryButton {
                background-color:  #DC2626;
                color: #FFFFFF;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight:  600;
                font-size: 14px;
                border: none;
                min-width: 120px;
            }
            
            QPushButton#secondaryButton:hover {
                background-color: #B91C1C;
            }
            
            QPushButton#secondaryButton:pressed {
                background-color: #991B1B;
            }
            
            QPushButton#actionButton {
                background-color:  #3B82F6;
                color: #FFFFFF;
                padding: 8px 4px;
                border-radius:  6px;
                border: none;
                font-weight: 600;
                font-size: 18px;
                min-width:  36px;
                max-width: 36px;
                min-height: 32px;
                max-height:  32px;
            }
            
            QPushButton#actionButton:hover {
                background-color: #2563EB;
            }
            
            QPushButton#deleteButton {
                background-color:  #EF4444;
                color:  #FFFFFF;
                padding:  8px 4px;
                border-radius: 6px;
                border: none;
                font-weight: 600;
                font-size: 18px;
                min-width:  36px;
                max-width: 36px;
                min-height: 32px;
                max-height: 32px;
            }
            
            QPushButton#deleteButton: hover {
                background-color:  #DC2626;
            }
            
            QTableWidget#modernTable {
                background-color: #FFFFFF;
                alternate-background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                gridline-color: #E5E7EB;
                color: #0F172A;
                selection-background-color: #EFF6FF;
                selection-color: #1E293B;
            }
            
            QTableWidget#modernTable::item {
                padding: 8px;
                color: #0F172A;
            }
            
            QTableWidget#modernTable::item:selected {
                background-color: #EFF6FF;
                color:  #1E293B;
            }
            
            QHeaderView::section {
                background-color: #F1F5F9;
                border: none;
                padding: 10px 8px;
                color: #475569;
                font-weight:  700;
                font-size: 12px;
                text-transform: uppercase;
            }
        """)

    def _load_expenses(self):
        """Carga los gastos adicionales desde el controller."""
        expenses = []
        try:
            if hasattr(self. controller, "get_additional_expenses"):
                expenses = self.controller.get_additional_expenses(
                    self.company_id,
                    self.current_month_str,
                    self.current_year_int
                ) or []
        except Exception as e:
            print(f"[EXPENSES] Error cargando gastos: {e}")
            QMessageBox.warning(self, "Error", f"No se pudieron cargar los gastos:\n{e}")

        self.table.setRowCount(0)
        total = 0.0

        for expense in expenses:
            row = self.table.rowCount()
            self.table.insertRow(row)

            fecha_str = ""
            try:
                fecha_raw = expense.get("date")
                if isinstance(fecha_raw, datetime.datetime):
                    fecha_str = fecha_raw.strftime("%d/%m/%Y")
                elif isinstance(fecha_raw, datetime. date):
                    fecha_str = fecha_raw.strftime("%d/%m/%Y")
                elif isinstance(fecha_raw, str):
                    fecha_str = fecha_raw[: 10]
            except: 
                fecha_str = str(expense.get("date", ""))[:10]

            self.table.setItem(row, 0, QTableWidgetItem(fecha_str))

            concepto = expense.get("concept", "")
            self.table.setItem(row, 1, QTableWidgetItem(concepto))

            monto = float(expense.get("amount", 0.0))
            total += monto
            monto_item = QTableWidgetItem(f"RD$ {monto: ,.2f}")
            monto_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 2, monto_item)

            categoria = expense.get("category", "")
            self.table.setItem(row, 3, QTableWidgetItem(categoria))

            notas = expense.get("notes", "")
            self.table.setItem(row, 4, QTableWidgetItem(notas))

            actions_widget = QFrame()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout. setContentsMargins(8, 4, 8, 4)
            actions_layout.setSpacing(6)

            btn_edit = QPushButton("✏️")
            btn_edit.setObjectName("actionButton")
            btn_edit.setToolTip("Editar gasto")
            btn_edit. clicked.connect(lambda checked, exp=expense: self._edit_expense(exp))

            btn_delete = QPushButton("🗑️")
            btn_delete.setObjectName("deleteButton")
            btn_delete. setToolTip("Eliminar gasto")
            btn_delete.clicked.connect(lambda checked, exp=expense: self._delete_expense(exp))

            actions_layout.addWidget(btn_edit)
            actions_layout.addWidget(btn_delete)
            actions_layout.addStretch()

            self.table.setCellWidget(row, 5, actions_widget)

        self.label_total.setText(f"RD$ {total:,.2f}")

    def _save_expense(self):
        """Guarda o actualiza un gasto adicional."""
        concepto = self.edit_concepto.text().strip()
        monto_str = self.edit_monto.text().strip().replace(",", "")
        
        if not concepto:
            QMessageBox.warning(self, "Validación", "El concepto es obligatorio.")
            self.edit_concepto.setFocus()
            return

        try:
            monto = float(monto_str or 0)
            if monto <= 0:
                raise ValueError("El monto debe ser mayor a cero.")
        except ValueError as e:
            QMessageBox. warning(self, "Validación", f"Monto inválido:\n{e}")
            self.edit_monto.setFocus()
            return

        qdate = self.date_picker.date()
        fecha = datetime.datetime(qdate.year(), qdate.month(), qdate.day())

        expense_data = {
            "company_id": self.company_id,
            "year": self.current_year_int,
            "month": self.current_month_str,
            "date": fecha,
            "concept": concepto,
            "amount": monto,
            "category": self.combo_categoria.currentText().strip(),
            "notes": self. edit_notas.toPlainText().strip(),
        }

        try: 
            if self.editing_expense_id:
                if hasattr(self.controller, "update_additional_expense"):
                    ok, msg = self.controller.update_additional_expense(
                        self. editing_expense_id, expense_data
                    )
                else:
                    ok, msg = False, "Método update_additional_expense no implementado."
            else:
                if hasattr(self.controller, "add_additional_expense"):
                    ok, msg = self.controller.add_additional_expense(expense_data)
                else: 
                    ok, msg = False, "Método add_additional_expense no implementado."

            if ok:
                QMessageBox.information(self, "Éxito", msg)
                self._clear_form()
                self._load_expenses()
            else:
                QMessageBox. warning(self, "Error", msg)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar el gasto:\n{e}")

    def _edit_expense(self, expense):
        """Carga un gasto en el formulario para edición."""
        self.editing_expense_id = expense.get("id")
        
        self.edit_concepto.setText(expense.get("concept", ""))
        self.edit_monto.setText(f"{float(expense.get('amount', 0.0)):.2f}")
        self.combo_categoria.setCurrentText(expense.get("category", ""))
        self.edit_notas.setPlainText(expense. get("notes", ""))

        try:
            fecha_raw = expense.get("date")
            if isinstance(fecha_raw, datetime. datetime):
                qdate = QDate(fecha_raw.year, fecha_raw.month, fecha_raw.day)
            elif isinstance(fecha_raw, datetime.date):
                qdate = QDate(fecha_raw.year, fecha_raw.month, fecha_raw.day)
            elif isinstance(fecha_raw, str):
                parts = fecha_raw[: 10].split("-")
                qdate = QDate(int(parts[0]), int(parts[1]), int(parts[2]))
            else:
                qdate = self._get_last_day_of_month()
            self.date_picker.setDate(qdate)
        except:
            self.date_picker.setDate(self._get_last_day_of_month())

        self.btn_cancelar.setVisible(True)
        self.btn_guardar.setText("💾 Actualizar")
        self.edit_concepto.setFocus()

    def _cancel_edit(self):
        """Cancela el modo edición."""
        self._clear_form()

    def _clear_form(self):
        """Limpia el formulario."""
        self.editing_expense_id = None
        self.edit_concepto.clear()
        self.edit_monto.clear()
        self.edit_notas.clear()
        self.combo_categoria.setCurrentIndex(0)
        self.date_picker.setDate(self._get_last_day_of_month())
        self.btn_guardar.setText("💾 Guardar")
        self.btn_cancelar.setVisible(False)

    def _delete_expense(self, expense):
        """Elimina un gasto adicional."""
        expense_id = expense.get("id")
        concepto = expense.get("concept", "desconocido")

        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Está seguro de eliminar el gasto '{concepto}'?",
            QMessageBox.StandardButton.Yes | QMessageBox. StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if hasattr(self.controller, "delete_additional_expense"):
                    ok, msg = self.controller.delete_additional_expense(expense_id)
                else: 
                    ok, msg = False, "Método delete_additional_expense no implementado."

                if ok:
                    QMessageBox.information(self, "Éxito", msg)
                    self._load_expenses()
                else:
                    QMessageBox.warning(self, "Error", msg)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al eliminar el gasto:\n{e}")