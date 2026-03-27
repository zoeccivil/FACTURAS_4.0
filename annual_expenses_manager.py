from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,  # ✅ Nuevo: Para layout compacto
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


class AnnualExpensesManager(QDialog):
    """
    Gestor de Gastos Adicionales ACUMULATIVOS por Año.
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

        self.setWindowTitle(f"Gastos Adicionales Anuales - {company_name} - {year_int}")
        self.resize(1100, 720) # Un poco más grande para respirar
        
        # ✅ HABILITAR BOTONES DE VENTANA (Max/Min/Cerrar)
        self.setWindowFlags(
            Qt.WindowType.Window 
            | Qt.WindowType.WindowMinimizeButtonHint 
            | Qt.WindowType.WindowMaximizeButtonHint 
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self._build_ui()
        self._load_concepts()

    def _build_ui(self):
            # Habilitar redimensionamiento del layout principal - COMPACTO
            root = QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)  # Reducido de 20 a 12
            root.setSpacing(10)  # Reducido de 16 a 10

            # === HEADER (Horizontal para ahorrar espacio vertical) - COMPACTO ===
            header_card = QFrame()
            header_card.setObjectName("headerCard")
            # Layout horizontal para el header: Título a la izq, Navegación a la der
            header_layout = QHBoxLayout(header_card)
            header_layout.setContentsMargins(12, 10, 12, 10)  # Reducido
            header_layout.setSpacing(10)  # Reducido

            # Títulos a la izquierda
            title_box = QVBoxLayout()
            title_box.setSpacing(4)
            title = QLabel(f"📊 Gastos Adicionales")
            title.setObjectName("dialogTitle") # Usa estilo definido en _apply_styles
            self.subtitle_label = QLabel() 
            self.subtitle_label.setObjectName("dialogSubtitle")
            title_box.addWidget(title)
            title_box.addWidget(self.subtitle_label)
            
            header_layout.addLayout(title_box)
            header_layout.addStretch() # Empuja la navegación a la derecha

            # Navegación a la derecha
            self.btn_prev_month = QPushButton("◀")
            self.btn_prev_month.setObjectName("navButton")
            self.btn_prev_month.setFixedWidth(40)
            self.btn_prev_month.clicked.connect(self._prev_month)

            self.month_label = QLabel()
            self.month_label.setObjectName("monthLabel") # ¡CLAVE PARA EL ESTILO AZUL!
            self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.month_label.setFixedWidth(160)

            self.btn_next_month = QPushButton("▶")
            self.btn_next_month.setObjectName("navButton")
            self.btn_next_month.setFixedWidth(40)
            self.btn_next_month.clicked.connect(self._next_month)

            header_layout.addWidget(self.btn_prev_month)
            header_layout.addWidget(self.month_label)
            header_layout.addWidget(self.btn_next_month)

            root.addWidget(header_card)

            # === FORMULARIO COMPACTO (GRID LAYOUT) ===
            form_card = QFrame()
            form_card.setObjectName("formCard")
            grid = QGridLayout(form_card)
            grid.setContentsMargins(12, 12, 12, 12)  # Reducido
            grid.setSpacing(10)  # Reducido
            # Configurar proporciones: Col 1 (Inputs largos) se estira más
            grid.setColumnStretch(1, 2) 
            grid.setColumnStretch(3, 1)

            # Título Formulario
            form_title = QLabel("Editar Concepto Anual")
            form_title.setStyleSheet("font-weight: 700; color: #1E293B; font-size: 14px; margin-bottom: 5px;")
            grid.addWidget(form_title, 0, 0, 1, 4)

            # Fila 1: Concepto y Categoría
            lbl_conc = QLabel("Concepto:")
            lbl_conc.setProperty("class", "fieldLabel")
            self.edit_concepto = QLineEdit()
            self.edit_concepto.setPlaceholderText("Nombre del gasto...")
            self.edit_concepto.setObjectName("modernInput")

            lbl_cat = QLabel("Categoría:")
            lbl_cat.setProperty("class", "fieldLabel")
            self.combo_categoria = QComboBox()
            self.combo_categoria.setObjectName("modernCombo")
            self.combo_categoria.addItems([
                "Nómina", "Servicios", "Alquiler", "Mantenimiento",
                "Publicidad", "Transporte", "Depreciación", "Otros"
            ])
            self.combo_categoria.setEditable(True)

            grid.addWidget(lbl_conc, 1, 0)
            grid.addWidget(self.edit_concepto, 1, 1)
            grid.addWidget(lbl_cat, 1, 2)
            grid.addWidget(self.combo_categoria, 1, 3)

            # Fila 2: Valor y Nota
            self.lbl_valor_mes = QLabel("Valor Mes:")
            self.lbl_valor_mes.setProperty("class", "fieldLabel")
            
            self.edit_valor = QLineEdit()
            self.edit_valor.setPlaceholderText("0.00")
            self.edit_valor.setObjectName("modernInput")
            self.edit_valor.setAlignment(Qt.AlignmentFlag.AlignRight)

            lbl_nota = QLabel("Nota:")
            lbl_nota.setProperty("class", "fieldLabel")
            self.edit_nota = QLineEdit() 
            self.edit_nota.setObjectName("modernInput")
            self.edit_nota.setPlaceholderText("Comentario opcional...")

            grid.addWidget(self.lbl_valor_mes, 2, 0)
            grid.addWidget(self.edit_valor, 2, 1)
            grid.addWidget(lbl_nota, 2, 2)
            grid.addWidget(self.edit_nota, 2, 3)

            # Fila 3: Botones de Acción
            btn_box = QHBoxLayout()
            btn_box.setSpacing(12)

            self.btn_guardar = QPushButton("💾 Guardar Valor")
            self.btn_guardar.setObjectName("primaryButton")
            self.btn_guardar.clicked.connect(self._save_value)

            self.btn_nuevo = QPushButton("➕ Limpiar")
            self.btn_nuevo.setObjectName("secondaryButton")
            self.btn_nuevo.clicked.connect(self._new_concept)

            self.btn_catalog = QPushButton("📚 Catálogo")
            self.btn_catalog.setObjectName("catalogButton")
            self.btn_catalog.setToolTip("Gestionar catálogo maestro")
            self.btn_catalog.clicked.connect(self._open_concept_catalog)

            self.btn_cancelar = QPushButton("Cancelar")
            self.btn_cancelar.setObjectName("cancelButton")
            self.btn_cancelar.clicked.connect(self._cancel_edit)
            self.btn_cancelar.setVisible(False)

            btn_box.addWidget(self.btn_guardar)
            btn_box.addWidget(self.btn_nuevo)
            btn_box.addWidget(self.btn_catalog)
            btn_box.addWidget(self.btn_cancelar)
            btn_box.addStretch()

            grid.addLayout(btn_box, 3, 0, 1, 4)

            root.addWidget(form_card)

            # === TABLA DE CONCEPTOS ===
            table_container = QVBoxLayout()
            table_container.setSpacing(5)
            table_label = QLabel("📋 Detalle de Conceptos:")
            table_label.setStyleSheet("font-weight: 700; color: #1E293B; font-size: 14px;")
            table_container.addWidget(table_label)

            self.table = QTableWidget()
            self.table.setObjectName("modernTable")
            self.table.setColumnCount(7)  # Aumentado de 5 a 7
            self.table.setHorizontalHeaderLabels([
                "Concepto", "Categoría", f"Valor {self._get_month_name()}", 
                "Mes Anterior", "Variación ($)", "Acumulado Año", "Acciones"
            ])
            
            # Tooltips para columnas nuevas
            header_item_ant = self.table.horizontalHeaderItem(3)
            if header_item_ant: 
                header_item_ant.setToolTip("Valor acumulado del mes anterior para comparación")
            
            header_item_var = self.table.horizontalHeaderItem(4)
            if header_item_var: 
                header_item_var.setToolTip("Diferencia entre mes actual y mes anterior")
            
            header_item_acum = self.table.horizontalHeaderItem(5)
            if header_item_acum: 
                header_item_acum.setToolTip("Suma acumulativa de Enero hasta el mes actual (valores se arrastran mes a mes)")

            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Concepto
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Categoría
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Valor Mes
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Mes Anterior
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Variación
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Acumulado Año
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Acciones
            self.table.setColumnWidth(6, 130)

            self.table.setAlternatingRowColors(True)
            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.table.verticalHeader().setVisible(False)
            self.table.verticalHeader().setDefaultSectionSize(40)  # Reducido de 44 a 40

            table_container.addWidget(self.table)
            root.addLayout(table_container)

            # === PANEL DE TOTALES CON 3 MÉTRICAS ===
            total_card = QFrame()
            total_card.setObjectName("totalCard")
            total_layout = QHBoxLayout(total_card)
            total_layout.setContentsMargins(15, 10, 15, 10)  # Reducido
            total_layout.setSpacing(20)
            
            # Métrica 1: Total Mes Actual
            metric1_box = QVBoxLayout()
            metric1_box.setSpacing(2)
            metric1_title = QLabel("TOTAL MES ACTUAL")
            metric1_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #6B7280; text-transform: uppercase;")
            metric1_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.label_total_mes = QLabel("RD$ 0.00")
            self.label_total_mes.setStyleSheet("font-size: 18px; font-weight: 800; color: #1E293B;")
            self.label_total_mes.setAlignment(Qt.AlignmentFlag.AlignCenter)
            metric1_box.addWidget(metric1_title)
            metric1_box.addWidget(self.label_total_mes)
            
            # Métrica 2: Variación vs Mes Anterior
            metric2_box = QVBoxLayout()
            metric2_box.setSpacing(2)
            metric2_title = QLabel("VARIACIÓN VS MES ANTERIOR")
            metric2_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #6B7280; text-transform: uppercase;")
            metric2_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.label_variacion = QLabel("RD$ 0.00")
            self.label_variacion.setStyleSheet("font-size: 18px; font-weight: 800; color: #3B82F6;")
            self.label_variacion.setAlignment(Qt.AlignmentFlag.AlignCenter)
            metric2_box.addWidget(metric2_title)
            metric2_box.addWidget(self.label_variacion)
            
            # Métrica 3: Total Acumulado Año
            metric3_box = QVBoxLayout()
            metric3_box.setSpacing(2)
            metric3_title = QLabel(f"TOTAL ACUMULADO AÑO {self.current_year_int}")
            metric3_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #6B7280; text-transform: uppercase;")
            metric3_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.label_total_acum = QLabel("RD$ 0.00")
            self.label_total_acum.setStyleSheet("font-size: 18px; font-weight: 800; color: #DC2626;")
            self.label_total_acum.setAlignment(Qt.AlignmentFlag.AlignCenter)
            metric3_box.addWidget(metric3_title)
            metric3_box.addWidget(self.label_total_acum)
            
            total_layout.addStretch()
            total_layout.addLayout(metric1_box)
            total_layout.addWidget(self._create_separator())
            total_layout.addLayout(metric2_box)
            total_layout.addWidget(self._create_separator())
            total_layout.addLayout(metric3_box)
            total_layout.addStretch()

            root.addWidget(total_card)

            # Aplicar estilos y actualizar textos
            self._apply_styles()
            self._update_labels()

    def _create_separator(self):
        """Crea una línea vertical separadora."""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #E5E7EB; max-width: 1px;")
        return separator

    def _apply_styles(self):
            self.setStyleSheet("""
                QDialog {
                    background-color: #F8F9FA;
                    font-family: 'Segoe UI', Inter, sans-serif;
                }

                QFrame#headerCard, QFrame#formCard {
                    background-color: #FFFFFF;
                    border-radius: 10px;
                    border: 1px solid #E5E7EB;
                }

                QFrame#totalCard {
                    background-color: #FFFFFF;
                    border-radius: 10px;
                    border: 2px solid #DC2626;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FEF2F2, stop:1 #FFFFFF);
                }
                
                QLabel#dialogTitle { font-size: 18px; font-weight: 700; color: #111827; }
                QLabel#dialogSubtitle { font-size: 12px; color: #6B7280; }
                
                QLabel.fieldLabel { font-weight: 600; color: #4B5563; font-size: 13px; }

                /* === ESTILO DEL LABEL DE MES (FONDO AZUL RESTAURADO) === */
                QLabel#monthLabel {
                    font-size: 14px; 
                    font-weight: 700; 
                    color: #1E293B;
                    padding: 4px 10px; 
                    background-color: #EFF6FF; /* Fondo Azul Claro */
                    border-radius: 6px; 
                    border: 1px solid #DBEAFE;
                    min-height: 20px;
                }

                /* Inputs */
                QLineEdit#modernInput {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 6px 10px;
                    color: #0F172A;
                    font-size: 13px;
                }
                QLineEdit#modernInput:focus { border-color: #3B82F6; border-width: 2px; }

                QComboBox#modernCombo {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 6px 10px;
                    color: #0F172A;
                    font-size: 13px;
                    font-weight: 500;
                }
                QComboBox#modernCombo:hover { border-color: #3B82F6; }
                QComboBox#modernCombo::drop-down { border: none; width: 30px; }
                QComboBox#modernCombo::down-arrow {
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 6px solid #64748B;
                    margin-right: 8px;
                }

                /* === BOTONES PRINCIPALES (COLORES VIVOS) === */
                QPushButton#primaryButton, 
                QPushButton#secondaryButton, 
                QPushButton#catalogButton, 
                QPushButton#cancelButton {
                    border-radius: 6px;
                    padding: 0 16px;
                    font-weight: 600;
                    font-size: 13px;
                    border: none;
                    height: 36px;
                    color: #FFFFFF;
                }

                QPushButton#primaryButton { background-color: #15803D; } /* Verde */
                QPushButton#primaryButton:hover { background-color: #166534; }

                QPushButton#secondaryButton { background-color: #3B82F6; } /* Azul */
                QPushButton#secondaryButton:hover { background-color: #2563EB; }

                QPushButton#catalogButton { background-color: #8B5CF6; } /* Violeta */
                QPushButton#catalogButton:hover { background-color: #7C3AED; }

                QPushButton#cancelButton { background-color: #DC2626; } /* Rojo */
                QPushButton#cancelButton:hover { background-color: #B91C1C; }

                /* Botones de Navegación (Flechas) */
                QPushButton#navButton {
                    background-color: #FFFFFF; /* Fondo Blanco */
                    color: #374151;
                    border: 1px solid #D1D5DB;
                    border-radius: 6px;
                    font-weight: 700;
                    font-size: 14px;
                }
                QPushButton#navButton:hover { background-color: #F3F4F6; }

                /* === TABLA === */
                QTableWidget#modernTable {
                    background-color: #FFFFFF;
                    alternate-background-color: #F8FAFC;
                    border: 1px solid #E5E7EB;
                    border-radius: 8px;
                    gridline-color: #F1F5F9;
                    color: #0F172A;
                }
                QHeaderView::section {
                    background-color: #F1F5F9;
                    border: none;
                    padding: 8px;
                    color: #64748B;
                    font-weight: 700;
                    font-size: 11px;
                    text-transform: uppercase;
                    border-bottom: 1px solid #E2E8F0;
                }

                /* Botones Pequeños en Tabla */
                QPushButton#actionButton, QPushButton#deleteButton, QPushButton#historyButton {
                    border-radius: 4px; border: none; font-size: 14px;
                    width: 30px; height: 30px;
                }
                
                QPushButton#actionButton { background-color: #EFF6FF; color: #2563EB; border: 1px solid #DBEAFE; }
                QPushButton#actionButton:hover { background-color: #DBEAFE; }

                QPushButton#historyButton { background-color: #F5F3FF; color: #7C3AED; border: 1px solid #DDD6FE; }
                QPushButton#historyButton:hover { background-color: #DDD6FE; }

                QPushButton#deleteButton { background-color: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
                QPushButton#deleteButton:hover { background-color: #FECACA; }
            """)        

    def _get_month_name(self):
        """Devuelve el nombre del mes actual."""
        for name, code in self.MONTHS_MAP.items():
            if code == self.current_month_str:
                return name
        return "Mes"

    def _update_labels(self):
        """Actualiza labels dinámicos según el mes actual."""
        month_name = self._get_month_name()
        
        self.month_label.setText(f"{month_name} {self.current_year_int}")
        self.subtitle_label.setText(
            f"{self.company_name} – Viendo valores acumulados hasta {month_name}"
        )
        self.lbl_valor_mes.setText(f"Valor Acumulado ({month_name}):")
        
        # Actualizar header de tabla
        if self.table.columnCount() >= 7:
            self.table.setHorizontalHeaderLabels([
                "Concepto", 
                "Categoría", 
                f"Valor {month_name}", 
                "Mes Anterior",
                "Variación ($)",
                "Acumulado Año", 
                "Acciones"
            ])
            # Tooltips
            header_item_ant = self.table.horizontalHeaderItem(3)
            if header_item_ant:
                prev_month_name = self._get_prev_month_name()
                header_item_ant.setToolTip(f"Valor acumulado de {prev_month_name}")
            
            header_item_acum = self.table.horizontalHeaderItem(5)
            if header_item_acum:
                header_item_acum.setToolTip(f"Suma acumulativa de Enero hasta {month_name}")
    
    def _get_prev_month_name(self):
        """Devuelve el nombre del mes anterior."""
        month_int = int(self.current_month_str)
        prev_month_int = month_int - 1 if month_int > 1 else 12
        prev_month_str = f"{prev_month_int:02d}"
        for name, code in self.MONTHS_MAP.items():
            if code == prev_month_str:
                return name
        return "Mes Anterior"

    def _prev_month(self):
        """Navega al mes anterior."""
        month_int = int(self.current_month_str)
        
        if month_int == 1:
            # Ir a diciembre del año anterior
            self.current_year_int -= 1
            self.current_month_str = "12"
        else:
            self.current_month_str = f"{month_int - 1:02d}"
        
        self._update_labels()
        self._load_concepts()

    def _next_month(self):
        """Navega al mes siguiente."""
        month_int = int(self.current_month_str)
        
        if month_int == 12:
            # Ir a enero del año siguiente
            self.current_year_int += 1
            self.current_month_str = "01"
        else:
            self.current_month_str = f"{month_int + 1:02d}"
        
        self._update_labels()
        self._load_concepts()

    def _load_concepts(self):
        """Carga los conceptos anuales con cálculo de variaciones."""
        concepts = []
        try:
            if hasattr(self.controller, "get_annual_expense_concepts"):
                concepts = self.controller.get_annual_expense_concepts(
                    self.company_id,
                    self.current_year_int
                ) or []
        except Exception as e:
            print(f"[ANNUAL_MANAGER] Error: {e}")
            QMessageBox.warning(self, "Error", f"Error cargando conceptos:\n{e}")

        self.table.setRowCount(0)
        total_month = 0.0  # Total del mes actual
        total_prev_month = 0.0  # Total del mes anterior
        total_acum_year = 0.0  # Total acumulado del año

        # Calcular mes anterior
        month_int = int(self.current_month_str)
        prev_month_int = month_int - 1 if month_int > 1 else 12
        prev_month_str = f"{prev_month_int:02d}"

        for concept_data in concepts:
            row = self.table.rowCount()
            self.table.insertRow(row)

            concept_name = concept_data.get("concept", "")
            category = concept_data.get("category", "")
            monthly_values = concept_data.get("monthly_values", {})

            # Valor mes actual (acumulativo)
            value_month = float(monthly_values.get(self.current_month_str, 0.0) or 0.0)
            
            # Arrastre de valor si es 0
            if value_month == 0.0:
                for m in range(month_int - 1, 0, -1):
                    m_str = f"{m:02d}"
                    if m_str in monthly_values:
                        value_month = float(monthly_values[m_str] or 0.0)
                        break

            # Valor mes anterior
            value_prev_month = float(monthly_values.get(prev_month_str, 0.0) or 0.0)
            
            # Arrastre de valor del mes anterior si es 0
            if value_prev_month == 0.0:
                for m in range(prev_month_int - 1, 0, -1):
                    m_str = f"{m:02d}"
                    if m_str in monthly_values:
                        value_prev_month = float(monthly_values[m_str] or 0.0)
                        break

            # Variación (diferencia entre mes actual y anterior)
            variation = value_month - value_prev_month

            # Acumulado anual: el valor del mes actual YA ES el acumulado
            # (porque el sistema es acumulativo)
            value_year = value_month

            # Sumar a los totales
            total_month += value_month
            total_prev_month += value_prev_month
            total_acum_year += value_year

            # Columna 0: Concepto
            self.table.setItem(row, 0, QTableWidgetItem(concept_name))
            
            # Columna 1: Categoría
            self.table.setItem(row, 1, QTableWidgetItem(category))

            # Columna 2: Valor Mes Actual
            item_month = QTableWidgetItem(f"RD$ {value_month:,.2f}")
            item_month.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 2, item_month)

            # Columna 3: Mes Anterior
            item_prev = QTableWidgetItem(f"RD$ {value_prev_month:,.2f}")
            item_prev.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_prev.setForeground(QColor("#6B7280"))
            self.table.setItem(row, 3, item_prev)

            # Columna 4: Variación ($)
            item_var = QTableWidgetItem(f"RD$ {variation:,.2f}")
            item_var.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            # Color según variación: Verde si disminuyó (positivo), Rojo si aumentó (negativo), Azul si cero
            # Usar tanto foreground como background para que el CSS no lo sobrescriba
            if variation > 0:
                item_var.setForeground(QColor("#10B981"))  # Verde (disminuyó el gasto - positivo)
                item_var.setBackground(QColor("#F0FDF4"))  # Fondo verde claro
                item_var.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            elif variation < 0:
                item_var.setForeground(QColor("#EF4444"))  # Rojo (aumentó el gasto - negativo)
                item_var.setBackground(QColor("#FEF2F2"))  # Fondo rojo claro
                item_var.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            else:
                item_var.setForeground(QColor("#3B82F6"))  # Azul (sin cambio)
                item_var.setBackground(QColor("#EFF6FF"))  # Fondo azul claro
                item_var.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.table.setItem(row, 4, item_var)

            # Columna 5: Acumulado Año
            item_year = QTableWidgetItem(f"RD$ {value_year:,.2f}")
            item_year.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_year.setForeground(QColor("#15803D"))
            item_year.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.table.setItem(row, 5, item_year)

            # Columna 6: Acciones
            actions_widget = QFrame()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(8, 4, 8, 4)
            actions_layout.setSpacing(6)

            btn_edit = QPushButton("✏️")
            btn_edit.setObjectName("actionButton")
            btn_edit.setToolTip("Editar valor del mes")
            btn_edit.clicked.connect(lambda checked, c=concept_data: self._edit_concept(c))

            btn_history = QPushButton("📊")
            btn_history.setObjectName("historyButton")
            btn_history.setToolTip("Ver histórico mensual")
            btn_history.clicked.connect(lambda checked, c=concept_data: self._show_history(c))

            btn_delete = QPushButton("🗑️")
            btn_delete.setObjectName("deleteButton")
            btn_delete.setToolTip("Eliminar concepto completo")
            btn_delete.clicked.connect(lambda checked, c=concept_data: self._delete_concept(c))

            actions_layout.addWidget(btn_edit)
            actions_layout.addWidget(btn_history)
            actions_layout.addWidget(btn_delete)
            actions_layout.addStretch()

            self.table.setCellWidget(row, 6, actions_widget)

        # Actualizar los 3 labels del footer
        self.label_total_mes.setText(f"RD$ {total_month:,.2f}")
        
        total_variation = total_month - total_prev_month
        self.label_variacion.setText(f"RD$ {total_variation:,.2f}")
        # Color según variación total: Verde (positivo), Rojo (negativo), Azul (cero)
        if total_variation > 0:
            self.label_variacion.setStyleSheet("font-size: 18px; font-weight: 800; color: #10B981;")  # Verde
        elif total_variation < 0:
            self.label_variacion.setStyleSheet("font-size: 18px; font-weight: 800; color: #EF4444;")  # Rojo
        else:
            self.label_variacion.setStyleSheet("font-size: 18px; font-weight: 800; color: #3B82F6;")  # Azul
        
        self.label_total_acum.setText(f"RD$ {total_acum_year:,.2f}")

    def _new_concept(self):
        """Limpia el formulario para crear un nuevo concepto."""
        self.editing_concept_id = None
        self.editing_concept_name = None
        self.edit_concepto.clear()
        self.edit_concepto.setEnabled(True)
        self.edit_valor.clear()
        self.edit_nota.clear()
        self.combo_categoria.setCurrentIndex(0)
        self.btn_guardar.setText("💾 Crear Concepto")
        self.btn_cancelar.setVisible(False)
        self.edit_concepto.setFocus()

    def _edit_concept(self, concept_data):
        """Carga un concepto para editar su valor del mes actual."""
        self.editing_concept_id = concept_data.get("id")
        self.editing_concept_name = concept_data.get("concept")
        
        self.edit_concepto.setText(self.editing_concept_name)
        self.edit_concepto.setEnabled(False) 
        
        self.combo_categoria.setCurrentText(concept_data.get("category", ""))
        
        monthly_values = concept_data.get("monthly_values", {})
        value_month = float(monthly_values.get(self.current_month_str, 0.0) or 0.0)
        
        if value_month == 0.0:
            month_int = int(self.current_month_str)
            for m in range(month_int - 1, 0, -1):
                m_str = f"{m:02d}"
                if m_str in monthly_values:  
                    value_month = float(monthly_values[m_str] or 0.0)
                    break
        
        self.edit_valor.setText(f"{value_month:.2f}")
        
        monthly_notes = concept_data.get("monthly_notes", {})
        note = monthly_notes.get(self.current_month_str, "")
        self.edit_nota.setText(note) # Usamos setText porque ahora es QLineEdit
        
        self.btn_guardar.setText("💾 Actualizar Valor")
        self.btn_cancelar.setVisible(True)
        self.edit_valor.setFocus()
        self.edit_valor.selectAll()

    def _cancel_edit(self):
        """Cancela la edición."""
        self._new_concept()

    def _save_value(self):
        """Guarda el valor acumulado del concepto para el mes actual."""
        concept_name = self.edit_concepto.text().strip()
        valor_str = self.edit_valor.text().strip().replace(",", "")
        
        if not concept_name: 
            QMessageBox.warning(self, "Validación", "El concepto es obligatorio.")
            self.edit_concepto.setFocus()
            return

        try:
            valor = float(valor_str or 0)
            if valor < 0:
                reply = QMessageBox.question(
                    self,
                    "Valor Negativo",
                    "El valor acumulado es negativo.  ¿Estás seguro?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
        except ValueError:
            QMessageBox.warning(self, "Validación", "El valor debe ser un número válido.")
            self.edit_valor.setFocus()
            return

        category = self.combo_categoria.currentText().strip()
        note = self.edit_nota.text().strip()

        try:
            if hasattr(self.controller, "update_annual_expense_value"):
                ok, msg = self.controller.update_annual_expense_value(
                    self.company_id,
                    self.current_year_int,
                    self.current_month_str,
                    concept_name,
                    category,
                    valor,
                    note
                )

                if ok:
                    QMessageBox.information(self, "Éxito", msg)
                    self._new_concept()
                    self._load_concepts()
                else:
                    QMessageBox.warning(self, "Error", msg)
            else:
                QMessageBox.critical(self, "Error", "Controller no implementado.")

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error al guardar:\n{e}")

    def _delete_concept(self, concept_data):
        """Elimina un concepto anual completo."""
        concept_id = concept_data.get("id")
        concept_name = concept_data.get("concept")

        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Estás seguro de eliminar el concepto '{concept_name}'?\n\n"
            f"Se eliminarán TODOS los valores mensuales del año {self.current_year_int}.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if hasattr(self.controller, "delete_annual_expense_concept"):
                    ok, msg = self.controller.delete_annual_expense_concept(concept_id)

                    if ok:
                        QMessageBox.information(self, "Éxito", msg)
                        self._load_concepts()
                    else:
                        QMessageBox.warning(self, "Error", msg)
                else:
                    QMessageBox.critical(self, "Error", "Método no implementado.")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al eliminar:\n{e}")

    def _show_history(self, concept_data):
        """Muestra el histórico mensual de un concepto."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel
        
        concept_name = concept_data.get("concept")
        monthly_values = concept_data.get("monthly_values", {})
        monthly_notes = concept_data.get("monthly_notes", {})

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Histórico:  {concept_name}")
        dlg.resize(600, 500)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel(f"📊 Histórico Mensual - {concept_name}")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0F172A;")
        layout.addWidget(title)

        subtitle = QLabel(f"Año {self.current_year_int}")
        subtitle.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(subtitle)

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Mes", "Valor Acumulado", "Nota"])
        table.setRowCount(12)

        for month in range(1, 13):
            month_str = f"{month:02d}"
            month_name = list(self.MONTHS_MAP.keys())[month - 1]

            value = float(monthly_values.get(month_str, 0.0) or 0.0)
            note = monthly_notes.get(month_str, "")

            if value == 0.0 and month > 1:
                for m in range(month - 1, 0, -1):
                    m_str = f"{m:02d}"
                    if m_str in monthly_values:
                        value = float(monthly_values[m_str] or 0.0)
                        break

            table.setItem(month - 1, 0, QTableWidgetItem(month_name))
            
            value_item = QTableWidgetItem(f"RD$ {value:,.2f}")
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if month_str == self.current_month_str:
                value_item.setForeground(QColor("#3B82F6"))
                value_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            table.setItem(month - 1, 1, value_item)
            
            table.setItem(month - 1, 2, QTableWidgetItem(note))

        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(True)
        layout.addWidget(table)

        dlg.exec()

    def _open_concept_catalog(self):
        """Abre diálogo para gestionar el catálogo de conceptos."""
        try:
            from concept_catalog_dialog import ConceptCatalogDialog
            
            dlg = ConceptCatalogDialog(
                parent=self,
                controller=self.controller,
                company_id=self.company_id,
                year=self.current_year_int
            )
            
            if dlg.exec():
                self._load_concepts()
        
        except ImportError as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el catálogo:\n{e}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error al abrir catálogo:\n{e}")