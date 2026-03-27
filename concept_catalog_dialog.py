from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QLineEdit, QComboBox,
    QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

class ConceptCatalogDialog(QDialog):
    """
    Diálogo para gestionar el catálogo maestro de conceptos.
    
    Permite: 
    - Ver conceptos disponibles
    - Crear nuevos conceptos
    - Propagar conceptos a todas las empresas
    """
    
    def __init__(self, parent, controller, company_id, year):
        super().__init__(parent)
        self.controller = controller
        self.company_id = company_id
        self.year = year
        
        self.setWindowTitle("Catálogo de Conceptos Anuales")
        self.resize(850, 600)
        self.setModal(True)
        
        self._build_ui()
        self._apply_styles()  # <--- APLICAMOS LOS ESTILOS
        self._load_catalog()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # === HEADER ===
        header_frame = QFrame()
        header_frame.setObjectName("headerCard")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 16, 20, 16)
        
        title = QLabel("📚 Catálogo Maestro de Conceptos")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A;")
        header_layout.addWidget(title)
        
        subtitle = QLabel(
            "Estos conceptos se propagarán a TODAS las empresas automáticamente."
        )
        subtitle.setStyleSheet("color: #64748B; font-size: 13px;")
        header_layout.addWidget(subtitle)
        
        layout.addWidget(header_frame)
        
        # === FORMULARIO NUEVO CONCEPTO ===
        form_frame = QFrame()
        form_frame.setObjectName("formCard")
        form_layout_container = QHBoxLayout(form_frame)
        form_layout_container.setContentsMargins(20, 16, 20, 16)
        form_layout_container.setSpacing(12)
        
        self.input_name = QLineEdit()
        self.input_name.setObjectName("modernInput") # <--- ID ESTILO
        self.input_name.setPlaceholderText("Nombre del concepto...")
        form_layout_container.addWidget(self.input_name, 2)
        
        self.combo_category = QComboBox()
        self.combo_category.setObjectName("modernCombo") # <--- ID ESTILO
        self.combo_category.addItems([
            "Nómina", "Servicios", "Alquiler", "Mantenimiento",
            "Publicidad", "Transporte", "Depreciación", "Otros"
        ])
        self.combo_category.setEditable(True)
        self.combo_category.setMinimumWidth(150)
        form_layout_container.addWidget(self.combo_category, 1)
        
        btn_create = QPushButton("➕ Crear y Propagar")
        btn_create.setObjectName("primaryButton") # <--- ID ESTILO
        btn_create.clicked.connect(self._create_and_propagate)
        form_layout_container.addWidget(btn_create)
        
        layout.addWidget(form_frame)
        
        # === TABLA ===
        self.table = QTableWidget()
        self.table.setObjectName("modernTable") # <--- ID ESTILO
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Concepto", "Categoría", "Descripción", "Acciones"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 140)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.table)
        
        # === BOTONES PIE ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_close = QPushButton("Cerrar")
        btn_close.setObjectName("secondaryButton") # <--- ID ESTILO
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)

    def _apply_styles(self):
        """Aplica los mismos estilos que la ventana principal."""
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }

            QFrame#headerCard, QFrame#formCard {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }

            /* INPUTS Y COMBOS */
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

            QComboBox#modernCombo {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px 12px;
                color: #0F172A;
                font-size: 13px;
                font-weight: 500;
            }
            QComboBox#modernCombo::drop-down { border: none; width: 30px; }
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
                selection-background-color: #EFF6FF;
                selection-color: #1E293B;
                color: #0F172A;
            }

            /* BOTONES */
            QPushButton#primaryButton {
                background-color: #15803D;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0px 20px;
                font-weight: 600;
                font-size: 14px;
                height: 40px;
            }
            QPushButton#primaryButton:hover { background-color: #166534; }

            QPushButton#secondaryButton {
                background-color: #64748B;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0px 20px;
                font-weight: 600;
                font-size: 14px;
                height: 40px;
                min-width: 100px;
            }
            QPushButton#secondaryButton:hover { background-color: #475569; }

            QPushButton#propagateButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 4px 12px;
                font-weight: 600;
                font-size: 13px;
                height: 30px;
            }
            QPushButton#propagateButton:hover { background-color: #2563EB; }

            /* TABLA */
            QTableWidget#modernTable {
                background-color: #FFFFFF;
                alternate-background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                gridline-color: #E5E7EB;
                color: #0F172A;
            }
            QTableWidget#modernTable::item { padding: 8px; }
            QHeaderView::section {
                background-color: #F1F5F9;
                border: none;
                padding: 10px 8px;
                color: #475569;
                font-weight: 700;
                font-size: 12px;
                text-transform: uppercase;
            }
        """)
    
    def _load_catalog(self):
        """Carga conceptos del catálogo."""
        if not hasattr(self.controller, "get_concept_catalog"):
            return
        
        concepts = self.controller.get_concept_catalog() or []
        
        self.table.setRowCount(0)
        
        for concept in concepts:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(concept.get("display_name", "")))
            self.table.setItem(row, 1, QTableWidgetItem(concept.get("category", "")))
            self.table.setItem(row, 2, QTableWidgetItem(concept.get("description", "")))
            
            # Widget contenedor para el botón para centrarlo
            btn_widget = QFrame()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 4, 4, 4)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            btn_propagate = QPushButton("🔄 Propagar")
            btn_propagate.setObjectName("propagateButton") # <--- ID ESTILO
            btn_propagate.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_propagate.clicked.connect(
                lambda checked, c=concept: self._propagate_concept(c)
            )
            
            btn_layout.addWidget(btn_propagate)
            self.table.setCellWidget(row, 3, btn_widget)
    
    def _create_and_propagate(self):
        """Crea concepto y lo propaga a todas las empresas."""
        name = self.input_name.text().strip()
        category = self.combo_category.currentText().strip()
        
        if not name:
            QMessageBox.warning(self, "Validación", "El nombre es obligatorio.")
            return
        
        # Generar concept_id
        concept_id = name.lower().replace(" ", "_").replace("ó", "o").replace("á", "a")
        concept_id = "". join(c for c in concept_id if c.isalnum() or c == "_")
        
        try:
            if hasattr(self.controller, "create_and_propagate_concept"):
                ok, msg = self.controller.create_and_propagate_concept(
                    concept_id, name, category, self.year  # ← AQUÍ ESTÁ EL AÑO
                )
                
                if ok:
                    QMessageBox.information(self, "Éxito", msg)
                    self.input_name.clear()
                    self._load_catalog()
                else:
                    QMessageBox.warning(self, "Error", msg)
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al crear concepto:\n{e}")
    
    def _propagate_concept(self, concept):
        """Propaga un concepto existente."""
        concept_id = concept.get("concept_id")
        display_name = concept.get("display_name")
        
        reply = QMessageBox.question(
            self,
            "Propagar Concepto",
            f"¿Propagar '{display_name}' a todas las empresas para {self.year}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if hasattr(self.controller, "propagate_concept_to_all_companies"):
                    ok, msg = self.controller.propagate_concept_to_all_companies(
                        concept_id, self.year
                    )
                    
                    if ok:
                        QMessageBox.information(self, "Éxito", msg)
                        # self.accept() # Opcional cerrar
                    else:
                        QMessageBox.warning(self, "Error", msg)
            
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error:\n{e}")