from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
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
    QWidget,
    QScrollArea
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor
import calendar


class AnnualIncomeManager(QDialog):
    """
    Gestor de Ingresos Adicionales ACUMULATIVOS por Año.
    Basado en AnnualExpensesManager pero con colores VERDES para diferenciar ingresos.
    """

    MONTHS_MAP = {
        "Enero": "01", "Febrero": "02", "Marzo": "03", "Abril": "04",
        "Mayo": "05", "Junio": "06", "Julio":  "07", "Agosto": "08",
        "Septiembre": "09", "Octubre":  "10", "Noviembre":  "11", "Diciembre": "12",
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
        
        self.editing_concept_id = None
        self.editing_concept_name = None

        self.setWindowTitle(f"Ingresos Adicionales Anuales - {company_name} - {year_int}")
        self.resize(1100, 720)
        
        # Habilitar botones de ventana
        self.setWindowFlags(
            Qt.WindowType.Window 
            | Qt.WindowType.WindowMinimizeButtonHint 
            | Qt.WindowType.WindowMaximizeButtonHint 
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self._build_ui()
        self._load_concepts()
        self._update_calculator()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # === HEADER ===
        header_card = QFrame()
        header_card.setObjectName("headerCard")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(10)

        # Títulos
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel(f"💰 Ingresos Adicionales")
        title.setObjectName("dialogTitle")
        self.subtitle_label = QLabel() 
        self.subtitle_label.setObjectName("dialogSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(self.subtitle_label)
        
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        # Navegación
        self.btn_prev_month = QPushButton("◀")
        self.btn_prev_month.setObjectName("navButton")
        self.btn_prev_month.setFixedWidth(40)
        self.btn_prev_month.clicked.connect(self._prev_month)

        self.month_label = QLabel()
        self.month_label.setObjectName("monthLabel")
        self.month_label.setFixedWidth(160)
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_next_month = QPushButton("▶")
        self.btn_next_month.setObjectName("navButton")
        self.btn_next_month.setFixedWidth(40)
        self.btn_next_month.clicked.connect(self._next_month)

        nav_box = QHBoxLayout()
        nav_box.setSpacing(8)
        nav_box.addWidget(self.btn_prev_month)
        nav_box.addWidget(self.month_label)
        nav_box.addWidget(self.btn_next_month)
        header_layout.addLayout(nav_box)

        root.addWidget(header_card)

        # === FORM (Grid compacto) ===
        form_card = QFrame()
        form_card.setObjectName("formCard")
        form_layout = QGridLayout(form_card)
        form_layout.setContentsMargins(16, 12, 16, 12)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(8)

        row = 0
        # Concepto
        form_layout.addWidget(QLabel("Concepto:"), row, 0)
        self.input_name = QLineEdit()
        self.input_name.setObjectName("inputField")
        self.input_name.setPlaceholderText("Ej: Rendimientos Bancarios")
        form_layout.addWidget(self.input_name, row, 1, 1, 3)

        row += 1
        # Categoría
        form_layout.addWidget(QLabel("Categoría:"), row, 0)
        self.input_category = QComboBox()
        self.input_category.setObjectName("inputCombo")
        self.input_category.addItems([
            "Financieros", 
            "Ajustes de Caja", 
            "Venta de Activos",
            "Otros Ingresos"
        ])
        self.input_category.setEditable(True)
        form_layout.addWidget(self.input_category, row, 1)

        # Valor
        form_layout.addWidget(QLabel(f"Valor Mes:"), row, 2)
        self.input_value = QLineEdit()
        self.input_value.setObjectName("inputField")
        self.input_value.setPlaceholderText("0.00")
        form_layout.addWidget(self.input_value, row, 3)

        row += 1
        # Descripción
        form_layout.addWidget(QLabel("Descripción:"), row, 0, Qt.AlignmentFlag.AlignTop)
        self.input_desc = QTextEdit()
        self.input_desc.setObjectName("inputTextArea")
        self.input_desc.setPlaceholderText("Descripción opcional")
        self.input_desc.setFixedHeight(60)
        form_layout.addWidget(self.input_desc, row, 1, 1, 3)

        row += 1
        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_save = QPushButton("💾 Guardar")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.clicked.connect(self._save_concept)

        self.btn_cancel = QPushButton("✖ Cancelar")
        self.btn_cancel.setObjectName("secondaryButton")
        self.btn_cancel.clicked.connect(self._cancel_edit)

        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addStretch()

        form_layout.addLayout(btn_layout, row, 0, 1, 4)

        root.addWidget(form_card)

        # === CALCULADORA DE BRECHA (GAP CALCULATOR) ===
        calc_card = QFrame()
        calc_card.setObjectName("calcCard")
        calc_layout = QVBoxLayout(calc_card)
        calc_layout.setContentsMargins(16, 12, 16, 12)
        calc_layout.setSpacing(8)
        
        calc_title = QLabel("🧮 Calculadora de Ajuste de Ingresos")
        calc_title.setObjectName("calcTitle")
        calc_layout.addWidget(calc_title)
        
        calc_grid = QGridLayout()
        calc_grid.setHorizontalSpacing(12)
        calc_grid.setVerticalSpacing(8)
        
        # Fila 1: Ingreso Facturado (lectura)
        calc_grid.addWidget(QLabel("Ingreso Facturado:"), 0, 0)
        self.calc_invoiced = QLineEdit()
        self.calc_invoiced.setObjectName("calcReadOnly")
        self.calc_invoiced.setReadOnly(True)
        self.calc_invoiced.setPlaceholderText("RD$ 0.00")
        calc_grid.addWidget(self.calc_invoiced, 0, 1)
        
        # Fila 2: Ingreso Real Objetivo (input)
        calc_grid.addWidget(QLabel("Ingreso Real Total:"), 1, 0)
        self.calc_real_input = QLineEdit()
        self.calc_real_input.setObjectName("inputField")
        self.calc_real_input.setPlaceholderText("Ej: 650000.00")
        self.calc_real_input.textChanged.connect(self._on_calc_real_changed)
        calc_grid.addWidget(self.calc_real_input, 1, 1)
        
        # Fila 3: Diferencia Calculada (resultado)
        calc_grid.addWidget(QLabel("Diferencia (Ajuste):"), 2, 0)
        self.calc_difference = QLineEdit()
        self.calc_difference.setObjectName("calcResult")
        self.calc_difference.setReadOnly(True)
        self.calc_difference.setPlaceholderText("RD$ 0.00")
        calc_grid.addWidget(self.calc_difference, 2, 1)
        
        # Botón "Usar este valor"
        self.btn_apply_calc = QPushButton("⬇ Usar este valor")
        self.btn_apply_calc.setObjectName("applyButton")
        self.btn_apply_calc.clicked.connect(self._apply_calculated_difference)
        calc_grid.addWidget(self.btn_apply_calc, 2, 2)
        
        calc_layout.addLayout(calc_grid)
        root.addWidget(calc_card)

        # === TABLA ===
        table_card = QFrame()
        table_card.setObjectName("tableCard")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(8, 8, 8, 8)

        self.table = QTableWidget()
        self.table.setObjectName("dataTable")
        # 7 columnas: Concepto, Categoría, Valor Mes, Mes Anterior, Variación, Acumulado Año, Acciones
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Concepto",
            "Categoría",
            f"Valor Mes",
            "Mes Anterior",
            "Variación ($)",
            "Acumulado Año",
            "Acciones"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 180)
        
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        
        # Tooltips
        self.table.horizontalHeaderItem(3).setToolTip(f"Valor del mes anterior para comparación")
        self.table.horizontalHeaderItem(4).setToolTip("Diferencia entre mes actual y anterior")
        self.table.horizontalHeaderItem(5).setToolTip(f"Suma acumulativa de Enero hasta el mes actual")

        table_layout.addWidget(self.table)
        root.addWidget(table_card, 1)

        # === FOOTER (3 métricas) ===
        self.total_card = QFrame()
        self.total_card.setObjectName("totalCard")
        total_layout = QHBoxLayout(self.total_card)
        total_layout.setContentsMargins(16, 12, 16, 12)
        total_layout.setSpacing(16)

        # Métrica 1: Total Mes Actual
        self.metric1_label = QLabel("TOTAL MES ACTUAL")
        self.metric1_label.setObjectName("metricTitle")
        self.metric1_value = QLabel("RD$ 0.00")
        self.metric1_value.setObjectName("metricValue")
        
        metric1_box = QVBoxLayout()
        metric1_box.setSpacing(4)
        metric1_box.addWidget(self.metric1_label, alignment=Qt.AlignmentFlag.AlignCenter)
        metric1_box.addWidget(self.metric1_value, alignment=Qt.AlignmentFlag.AlignCenter)
        
        total_layout.addLayout(metric1_box)
        total_layout.addWidget(self._create_separator())

        # Métrica 2: Variación vs Mes Anterior
        self.metric2_label = QLabel("VARIACIÓN VS MES ANTERIOR")
        self.metric2_label.setObjectName("metricTitle")
        self.metric2_value = QLabel("RD$ 0.00")
        self.metric2_value.setObjectName("metricValue")
        
        metric2_box = QVBoxLayout()
        metric2_box.setSpacing(4)
        metric2_box.addWidget(self.metric2_label, alignment=Qt.AlignmentFlag.AlignCenter)
        metric2_box.addWidget(self.metric2_value, alignment=Qt.AlignmentFlag.AlignCenter)
        
        total_layout.addLayout(metric2_box)
        total_layout.addWidget(self._create_separator())

        # Métrica 3: Total Acumulado Año
        self.metric3_label = QLabel("TOTAL ACUMULADO AÑO")
        self.metric3_label.setObjectName("metricTitle")
        self.metric3_value = QLabel("RD$ 0.00")
        self.metric3_value.setObjectName("metricValue")
        
        metric3_box = QVBoxLayout()
        metric3_box.setSpacing(4)
        metric3_box.addWidget(self.metric3_label, alignment=Qt.AlignmentFlag.AlignCenter)
        metric3_box.addWidget(self.metric3_value, alignment=Qt.AlignmentFlag.AlignCenter)
        
        total_layout.addLayout(metric3_box)

        root.addWidget(self.total_card)

        self._apply_styles()
        self._update_labels()

    def _create_separator(self):
        """Crea una línea vertical separadora."""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #E2E8F0;")
        line.setFixedWidth(1)
        return line

    def _apply_styles(self):
        """Estilos CSS - COLORES VERDES para ingresos."""
        self.setStyleSheet("""
            QDialog {
                background-color: #F8FAFC;
            }
            
            #headerCard, #formCard, #tableCard, #totalCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
            
            #dialogTitle {
                font-size: 20px;
                font-weight: bold;
                color: #0F172A;
            }
            
            #dialogSubtitle {
                font-size: 13px;
                color: #64748B;
            }
            
            #navButton {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                color: #475569;
                font-weight: 600;
                padding: 6px;
            }
            
            #navButton:hover {
                background-color: #F1F5F9;
                border-color: #94A3B8;
            }
            
            #monthLabel {
                font-size: 14px;
                font-weight: 600;
                color: #1E293B;
            }
            
            QLabel {
                color: #1E293B;
                font-size: 13px;
            }
            
            #inputField, #inputCombo {
                padding: 8px 12px;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                background-color: #FFFFFF;
                font-size: 13px;
                color: #0F172A;
            }
            
            #inputField:focus, #inputCombo:focus {
                border: 2px solid #15803D;
                outline: none;
            }
            
            #inputTextArea {
                padding: 8px;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                background-color: #FFFFFF;
                font-size: 13px;
                color: #0F172A;
            }
            
            #inputTextArea:focus {
                border: 2px solid #15803D;
            }
            
            #primaryButton {
                background-color: #15803D;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-weight: 600;
                font-size: 13px;
            }
            
            #primaryButton:hover {
                background-color: #166534;
            }
            
            #secondaryButton {
                background-color: #F1F5F9;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 10px 24px;
                font-weight: 600;
                font-size: 13px;
            }
            
            #secondaryButton:hover {
                background-color: #E2E8F0;
            }
            
            #dataTable {
                background-color: #FFFFFF;
                border: none;
                gridline-color: #E2E8F0;
                selection-background-color: #DBEAFE;
                selection-color: #0F172A;
                font-size: 13px;
                color: #0F172A;
            }
            
            #dataTable::item {
                padding: 8px;
            }
            
            #dataTable::item:selected {
                background-color: #DBEAFE;
                color: #111827;
            }
            
            #dataTable QHeaderView::section {
                background-color: #F8FAFC;
                color: #475569;
                font-weight: 600;
                font-size: 12px;
                padding: 10px 8px;
                border: none;
                border-bottom: 2px solid #15803D;
                border-right: 1px solid #E2E8F0;
            }
            
            #totalCard {
                border: 2px solid #15803D;
            }
            
            #metricTitle {
                font-size: 11px;
                font-weight: 600;
                color: #64748B;
                letter-spacing: 0.5px;
            }
            
            #metricValue {
                font-size: 20px;
                font-weight: bold;
                color: #0F172A;
            }
            
            QPushButton {
                background-color: #15803D;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 12px;
            }
            
            QPushButton:hover {
                background-color: #166534;
            }
            
            #calcCard {
                background-color: #F0FDF4;
                border: 2px solid #86EFAC;
                border-radius: 8px;
                padding: 12px;
            }
            
            #calcTitle {
                font-size: 14px;
                font-weight: 600;
                color: #15803D;
            }
            
            #calcReadOnly {
                background-color: #E0F2FE;
                border: 1px solid #BAE6FD;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                color: #0C4A6E;
                font-weight: 600;
            }
            
            #calcResult {
                background-color: #FEF3C7;
                border: 2px solid #FCD34D;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                color: #92400E;
                font-weight: bold;
            }
            
            #applyButton {
                background-color: #15803D;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
            }
            
            #applyButton:hover {
                background-color: #166534;
            }
            
            #applyButton:pressed {
                background-color: #14532D;
            }
        """)

    def _update_labels(self):
        """Actualiza labels dinámicamente."""
        month_name = self._get_month_name(self.current_month_str)
        self.subtitle_label.setText(f"{self.company_name} - {month_name} {self.current_year_int}")
        self.month_label.setText(f"{month_name} {self.current_year_int}")
        
        # Actualizar tooltips
        prev_month_name = self._get_prev_month_name()
        self.table.horizontalHeaderItem(3).setToolTip(f"Valor de {prev_month_name} para comparación")
        self.table.horizontalHeaderItem(5).setToolTip(f"Suma acumulativa de Enero hasta {month_name}")

    def _get_month_name(self, month_str):
        """Obtiene nombre del mes."""
        for name, value in self.MONTHS_MAP.items():
            if value == month_str:
                return name
        return "Mes"

    def _get_prev_month_name(self):
        """Devuelve el nombre del mes anterior."""
        current_month_int = int(self.current_month_str)
        if current_month_int == 1:
            prev_month_int = 12
        else:
            prev_month_int = current_month_int - 1
        
        prev_month_str = f"{prev_month_int:02d}"
        return self._get_month_name(prev_month_str)

    def _prev_month(self):
        """Navega al mes anterior."""
        current_month_int = int(self.current_month_str)
        if current_month_int == 1:
            self.current_month_str = "12"
            self.current_year_int -= 1
        else:
            self.current_month_str = f"{current_month_int - 1:02d}"
        
        self._update_labels()
        self._load_concepts()
        self._update_calculator()

    def _next_month(self):
        """Navega al mes siguiente."""
        current_month_int = int(self.current_month_str)
        if current_month_int == 12:
            self.current_month_str = "01"
            self.current_year_int += 1
        else:
            self.current_month_str = f"{current_month_int + 1:02d}"
        
        self._update_labels()
        self._load_concepts()
        self._update_calculator()
    
    def _update_calculator(self):
        """Actualiza el campo de ingreso facturado al cambiar de mes."""
        try:
            # Obtener summary del mes/año actual
            summary = self.controller.get_profit_summary(
                company_id=self.company_id,
                month_str=self.current_month_str,
                year_int=self.current_year_int
            )
            
            # Extraer ingreso facturado
            total_invoiced = summary.get("total_income", 0.0)
            
            # Actualizar campo
            self.calc_invoiced.setText(f"RD$ {total_invoiced:,.2f}")
            
            # Limpiar los otros campos al cambiar de mes
            self.calc_real_input.clear()
            self.calc_difference.clear()
            
        except Exception as e:
            print(f"[CALCULATOR] Error al actualizar calculadora: {str(e)}")
            self.calc_invoiced.setText("RD$ 0.00")
    
    def _on_calc_real_changed(self):
        """Calcula la diferencia automáticamente cuando el usuario escribe."""
        try:
            # Obtener ingreso facturado
            invoiced_text = self.calc_invoiced.text().replace("RD$ ", "").replace(",", "")
            invoiced = float(invoiced_text) if invoiced_text else 0.0
            
            # Obtener ingreso real
            real_text = self.calc_real_input.text().strip().replace(",", "")
            if not real_text:
                self.calc_difference.clear()
                return
            
            real = float(real_text)
            
            # Calcular diferencia
            difference = real - invoiced
            
            # Actualizar campo resultado
            self.calc_difference.setText(f"RD$ {difference:,.2f}")
            
        except ValueError:
            self.calc_difference.setText("Valor inválido")
        except Exception as e:
            print(f"[CALCULATOR] Error al calcular: {str(e)}")
            self.calc_difference.clear()
    
    def _apply_calculated_difference(self):
        """Copia la diferencia calculada al campo de valor principal."""
        try:
            diff_text = self.calc_difference.text().replace("RD$ ", "").replace(",", "")
            if not diff_text or diff_text == "Valor inválido":
                QMessageBox.warning(self, "Aviso", "No hay diferencia calculada para aplicar.")
                return
            
            # Copiar al campo principal
            self.input_value.setText(diff_text)
            
            QMessageBox.information(
                self, 
                "Valor Aplicado", 
                f"El valor de ajuste ({diff_text}) ha sido copiado al campo 'Valor Mes'.\n\n"
                "Ahora puede ingresar el concepto y guardar."
            )
            
            # Dar foco al campo de concepto si está vacío
            if not self.input_name.text().strip():
                self.input_name.setFocus()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al aplicar valor: {str(e)}")


    def _load_concepts(self):
        """Carga conceptos y calcula totales."""
        self.table.setRowCount(0)
        
        try:
            concepts = self.controller.get_annual_income_concepts(
                self.company_id, self.current_year_int
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar conceptos: {str(e)}")
            return

        # Calcular mes anterior
        current_month_int = int(self.current_month_str)
        if current_month_int == 1:
            prev_month_str = "12"
            prev_year_int = self.current_year_int - 1
        else:
            prev_month_str = f"{current_month_int - 1:02d}"
            prev_year_int = self.current_year_int

        total_month = 0.0
        total_prev_month = 0.0
        total_year = 0.0

        for concept in concepts:
            concept_id = concept.get("id", "")
            name = concept.get("name", "")
            category = concept.get("category", "")
            
            monthly_values = concept.get("months", {}).get(str(self.current_year_int), {})
            
            # Valor mes actual (acumulado)
            value_month = float(monthly_values.get(self.current_month_str, 0.0) or 0.0)
            
            # Valor mes anterior
            if prev_year_int == self.current_year_int:
                value_prev = float(monthly_values.get(prev_month_str, 0.0) or 0.0)
            else:
                # Buscar en año anterior
                prev_year_values = concept.get("months", {}).get(str(prev_year_int), {})
                value_prev = float(prev_year_values.get(prev_month_str, 0.0) or 0.0)
            
            # Variación
            variation = value_month - value_prev
            
            # Acumulado año (el valor del mes actual YA ES el acumulado)
            value_year = value_month
            
            total_month += value_month
            total_prev_month += value_prev
            total_year += value_year

            # Agregar fila
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            
            # Columna 0: Concepto
            item_name = QTableWidgetItem(name)
            item_name.setData(Qt.ItemDataRole.UserRole, concept_id)
            self.table.setItem(row_position, 0, item_name)
            
            # Columna 1: Categoría
            self.table.setItem(row_position, 1, QTableWidgetItem(category))
            
            # Columna 2: Valor Mes
            item_val = QTableWidgetItem(f"RD$ {value_month:,.2f}")
            item_val.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            font_bold = QFont()
            font_bold.setBold(True)
            item_val.setFont(font_bold)
            self.table.setItem(row_position, 2, item_val)
            
            # Columna 3: Mes Anterior
            item_prev = QTableWidgetItem(f"RD$ {value_prev:,.2f}")
            item_prev.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_position, 3, item_prev)
            
            # Columna 4: Variación (con colores)
            item_var = QTableWidgetItem(f"RD$ {variation:+,.2f}")
            item_var.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_var.setFont(font_bold)
            
            # Colores (invertidos vs gastos: positivo = verde, negativo = rojo)
            if variation > 0:
                item_var.setForeground(QColor("#15803D"))  # Verde oscuro
                item_var.setBackground(QColor("#F0FDF4"))  # Verde claro
            elif variation < 0:
                item_var.setForeground(QColor("#DC2626"))  # Rojo oscuro
                item_var.setBackground(QColor("#FEF2F2"))  # Rojo claro
            else:
                item_var.setForeground(QColor("#3B82F6"))  # Azul
                item_var.setBackground(QColor("#EFF6FF"))  # Azul claro
            
            self.table.setItem(row_position, 4, item_var)
            
            # Columna 5: Acumulado Año
            item_year = QTableWidgetItem(f"RD$ {value_year:,.2f}")
            item_year.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_year.setFont(font_bold)
            self.table.setItem(row_position, 5, item_year)
            
            # Columna 6: Acciones
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)
            
            btn_edit = QPushButton("✏ Editar")
            btn_edit.clicked.connect(lambda checked, cid=concept_id: self._edit_concept(cid))
            
            btn_hist = QPushButton("📊 Histórico")
            btn_hist.clicked.connect(lambda checked, cid=concept_id: self._show_history(cid))
            
            btn_delete = QPushButton("🗑 Eliminar")
            btn_delete.clicked.connect(lambda checked, cid=concept_id: self._delete_concept(cid))
            
            actions_layout.addWidget(btn_edit)
            actions_layout.addWidget(btn_hist)
            actions_layout.addWidget(btn_delete)
            actions_layout.addStretch()
            
            self.table.setCellWidget(row_position, 6, actions_widget)

        # Actualizar métricas del footer
        self.metric1_value.setText(f"RD$ {total_month:,.2f}")
        
        total_variation = total_month - total_prev_month
        variation_text = f"RD$ {total_variation:+,.2f}"
        self.metric2_value.setText(variation_text)
        
        # Color de variación total
        if total_variation > 0:
            self.metric2_value.setStyleSheet("color: #15803D; font-weight: bold; font-size: 20px;")
        elif total_variation < 0:
            self.metric2_value.setStyleSheet("color: #DC2626; font-weight: bold; font-size: 20px;")
        else:
            self.metric2_value.setStyleSheet("color: #3B82F6; font-weight: bold; font-size: 20px;")
        
        self.metric3_value.setText(f"RD$ {total_year:,.2f}")

    def _save_concept(self):
        """Guarda o actualiza concepto."""
        name = self.input_name.text().strip()
        category = self.input_category.currentText().strip()
        value_str = self.input_value.text().strip()
        description = self.input_desc.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "Validación", "El concepto es obligatorio.")
            return

        try:
            value = float(value_str) if value_str else 0.0
        except ValueError:
            QMessageBox.warning(self, "Validación", "El valor debe ser un número.")
            return

        try:
            if self.editing_concept_id:
                # Actualizar valor del mes actual
                self.controller.update_annual_income_value(
                    self.company_id,
                    self.current_year_int,
                    self.current_month_str,
                    self.editing_concept_id,
                    value
                )
            else:
                # Crear nuevo concepto
                self.controller.create_annual_income_concept(
                    self.company_id,
                    self.current_year_int,
                    self.current_month_str,
                    name,
                    category,
                    description,
                    value
                )
            
            self._cancel_edit()
            self._load_concepts()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar: {str(e)}")

    def _edit_concept(self, concept_id):
        """Carga concepto para editar."""
        try:
            concepts = self.controller.get_annual_income_concepts(
                self.company_id, self.current_year_int
            )
            
            for concept in concepts:
                if concept.get("id") == concept_id:
                    self.editing_concept_id = concept_id
                    self.editing_concept_name = concept.get("name", "")
                    
                    self.input_name.setText(concept.get("name", ""))
                    self.input_name.setEnabled(False)
                    
                    category = concept.get("category", "")
                    idx = self.input_category.findText(category)
                    if idx >= 0:
                        self.input_category.setCurrentIndex(idx)
                    else:
                        self.input_category.setCurrentText(category)
                    
                    monthly_values = concept.get("months", {}).get(str(self.current_year_int), {})
                    value = monthly_values.get(self.current_month_str, 0.0)
                    self.input_value.setText(str(value))
                    
                    self.input_desc.setPlainText(concept.get("description", ""))
                    
                    break
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar concepto: {str(e)}")

    def _cancel_edit(self):
        """Cancela edición."""
        self.editing_concept_id = None
        self.editing_concept_name = None
        self.input_name.clear()
        self.input_name.setEnabled(True)
        self.input_category.setCurrentIndex(0)
        self.input_value.clear()
        self.input_desc.clear()

    def _delete_concept(self, concept_id):
        """Elimina concepto."""
        reply = QMessageBox.question(
            self,
            "Confirmar",
            "¿Está seguro de eliminar este concepto?\nSe perderán todos los valores del año.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.controller.delete_annual_income_concept(
                    self.company_id, concept_id
                )
                self._load_concepts()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al eliminar: {str(e)}")

    def _show_history(self, concept_id):
        """Muestra histórico del concepto."""
        try:
            concepts = self.controller.get_annual_income_concepts(
                self.company_id, self.current_year_int
            )
            
            concept_data = None
            for concept in concepts:
                if concept.get("id") == concept_id:
                    concept_data = concept
                    break
            
            if not concept_data:
                QMessageBox.warning(self, "Error", "Concepto no encontrado.")
                return
            
            name = concept_data.get("name", "Sin nombre")
            monthly_values = concept_data.get("months", {}).get(str(self.current_year_int), {})
            
            history_text = f"Histórico de '{name}' - Año {self.current_year_int}\n\n"
            
            for month_num in range(1, 13):
                month_str = f"{month_num:02d}"
                month_name = self._get_month_name(month_str)
                value = monthly_values.get(month_str, 0.0)
                history_text += f"{month_name}: RD$ {value:,.2f}\n"
            
            QMessageBox.information(self, "Histórico del Concepto", history_text)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al mostrar histórico: {str(e)}")
