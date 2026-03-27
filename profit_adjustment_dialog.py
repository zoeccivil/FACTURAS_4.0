from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QMessageBox,
    QTextEdit,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDoubleValidator
import datetime


class ProfitAdjustmentDialog(QDialog):
    """
    Diálogo para ajustar manualmente la utilidad cuando difiere de la contabilidad interna. 
    
    Crea/actualiza un gasto adicional llamado "AJUSTE DE UTILIDADES" con la diferencia.
    """

    def __init__(
        self,
        parent,
        controller,
        company_id,
        company_name:  str,
        month_str: str,
        year_int: int,
        calculated_profit: float,
    ):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.company_id = company_id
        self. company_name = company_name
        self.month_str = month_str
        self.year_int = year_int
        self.calculated_profit = calculated_profit
        
        self.setWindowTitle("Ajuste Manual de Utilidad")
        self.resize(600, 400)
        self.setModal(True)
        
        self._build_ui()
        self._check_existing_adjustment()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # === HEADER ===
        header_card = QFrame()
        header_card.setObjectName("headerCard")
        header_layout = QVBoxLayout(header_card)
        header_layout. setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(4)

        title = QLabel("⚖️ Ajuste de Utilidad")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A;")
        
        subtitle = QLabel(
            f"Ajusta la utilidad del sistema para que coincida con tu contabilidad interna"
        )
        subtitle.setStyleSheet("font-size: 12px; color: #64748B;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header_card)

        # === INFO CARD ===
        info_card = QFrame()
        info_card.setObjectName("infoCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 16, 20, 16)
        info_layout.setSpacing(12)

        # Empresa y periodo
        company_label = QLabel(f"📊 {self.company_name}")
        company_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #1E293B;")
        info_layout.addWidget(company_label)

        month_names = {
            "01": "Enero", "02": "Febrero", "03":  "Marzo", "04": "Abril",
            "05":  "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
            "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
        }
        month_name = month_names.get(self.month_str, self.month_str)
        
        period_label = QLabel(f"📅 Periodo: {month_name} {self.year_int}")
        period_label.setStyleSheet("font-size: 12px; color: #64748B;")
        info_layout. addWidget(period_label)

        root.addWidget(info_card)

        # === VALORES ===
        values_card = QFrame()
        values_card. setObjectName("valuesCard")
        values_layout = QVBoxLayout(values_card)
        values_layout.setContentsMargins(20, 16, 20, 16)
        values_layout.setSpacing(16)

        # Utilidad calculada (readonly)
        calc_row = QHBoxLayout()
        calc_row.setSpacing(12)
        
        calc_label = QLabel("Utilidad Calculada:")
        calc_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #475569;")
        calc_row.addWidget(calc_label)
        
        self.calc_value = QLabel(f"RD$ {self.calculated_profit:,.2f}")
        color = "#15803D" if self.calculated_profit >= 0 else "#DC2626"
        self.calc_value.setStyleSheet(f"font-size: 16px; font-weight: 700; color:  {color};")
        calc_row.addWidget(self.calc_value)
        calc_row.addStretch()
        
        values_layout.addLayout(calc_row)

        # Línea separadora
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape. HLine)
        sep.setStyleSheet("background-color: #E5E7EB;")
        values_layout.addWidget(sep)

        # Utilidad real (input)
        real_row = QHBoxLayout()
        real_row.setSpacing(12)
        
        real_label = QLabel("Utilidad Real (Contabilidad):")
        real_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #475569;")
        real_row.addWidget(real_label)
        
        self.real_input = QLineEdit()
        self.real_input.setObjectName("modernInput")
        self.real_input.setPlaceholderText("Ingrese la utilidad según su contabilidad")
        self.real_input.setAlignment(Qt.AlignmentFlag. AlignRight)
        self.real_input.setMinimumWidth(200)
        
        # Validador para solo números
        validator = QDoubleValidator()
        validator.setDecimals(2)
        validator.setNotation(QDoubleValidator. Notation.StandardNotation)
        self.real_input.setValidator(validator)
        
        self.real_input.textChanged.connect(self._calculate_difference)
        real_row.addWidget(self. real_input)
        real_row.addStretch()
        
        values_layout.addLayout(real_row)

        # Diferencia (auto-calculada)
        diff_row = QHBoxLayout()
        diff_row.setSpacing(12)
        
        diff_label = QLabel("Diferencia (Ajuste):")
        diff_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #475569;")
        diff_row.addWidget(diff_label)
        
        self.diff_value = QLabel("RD$ 0.00")
        self.diff_value.setStyleSheet("font-size: 15px; font-weight: 700; color: #64748B;")
        diff_row.addWidget(self.diff_value)
        diff_row.addStretch()
        
        values_layout.addLayout(diff_row)

        # Explicación
        explain_label = QLabel(
            "💡 El ajuste se guardará como gasto adicional con categoría 'Ajuste Contable'"
        )
        explain_label.setStyleSheet("font-size: 11px; color: #6B7280; font-style: italic;")
        explain_label.setWordWrap(True)
        values_layout. addWidget(explain_label)

        root.addWidget(values_card)

        # === NOTAS ===
        notes_label = QLabel("Notas del Ajuste (opcional):")
        notes_label. setStyleSheet("font-size:  13px; font-weight:  600; color: #475569;")
        root.addWidget(notes_label)

        self.notes_input = QTextEdit()
        self.notes_input.setObjectName("modernTextEdit")
        self.notes_input.setPlaceholderText(
            "Ej: Ajuste por depreciación no contabilizada, provisiones, etc."
        )
        self.notes_input.setMaximumHeight(80)
        root.addWidget(self.notes_input)

        # === BOTONES ===
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.btn_save = QPushButton("💾 Guardar Ajuste")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.setMinimumHeight(40)
        self.btn_save.clicked.connect(self._save_adjustment)

        btn_cancel = QPushButton("❌ Cancelar")
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.setMinimumHeight(40)
        btn_cancel. clicked.connect(self.reject)

        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self.btn_save)

        root.addLayout(btn_row)

        # === ESTILOS ===
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }
            
            QFrame#headerCard {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }
            
            QFrame#infoCard {
                background-color: #EFF6FF;
                border-radius: 12px;
                border: 1px solid #BFDBFE;
            }
            
            QFrame#valuesCard {
                background-color:  #FFFFFF;
                border-radius: 12px;
                border: 2px solid #3B82F6;
            }
            
            QLineEdit#modernInput {
                background-color: #FFFFFF;
                border: 2px solid #CBD5E1;
                border-radius: 6px;
                padding: 10px 12px;
                color: #0F172A;
                font-size: 14px;
                font-weight: 600;
            }
            
            QLineEdit#modernInput: focus {
                border-color:  #3B82F6;
            }
            
            QTextEdit#modernTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px;
                color: #0F172A;
                font-size: 13px;
            }
            
            QPushButton#primaryButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-weight: 600;
                font-size: 14px;
                min-width: 160px;
            }
            
            QPushButton#primaryButton: hover {
                background-color:  #2563EB;
            }
            
            QPushButton#secondaryButton {
                background-color: #F9FAFB;
                color: #374151;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                padding: 10px 24px;
                font-weight:  600;
                font-size: 14px;
                min-width: 120px;
            }
            
            QPushButton#secondaryButton:hover {
                background-color: #E5E7EB;
            }
        """)

    def _check_existing_adjustment(self):
        """Verifica si ya existe un ajuste ACUMULATIVO para este periodo y lo carga."""
        try:
            if not hasattr(self. controller, "get_annual_expense_concepts"):
                return

            # Obtener conceptos del año
            concepts = self.controller.get_annual_expense_concepts(
                self.company_id,
                self.year_int
            ) or []

            # Buscar concepto "AJUSTE CONTABLE"
            for concept in concepts:
                if concept.get("concept") == "AJUSTE CONTABLE":
                    monthly_values = concept.get("monthly_values", {})
                    monthly_notes = concept.get("monthly_notes", {})
                    
                    # Obtener valor del mes actual
                    adjustment_amount = float(monthly_values.get(self.month_str, 0.0) or 0.0)
                    
                    if adjustment_amount != 0:
                        # Calcular utilidad real a partir del ajuste
                        # ajuste positivo = gasto → utilidad real = calculada - ajuste
                        real_profit = self.calculated_profit - adjustment_amount
                        
                        self.real_input.setText(f"{real_profit:.2f}")
                        
                        # Cargar notas
                        notes = monthly_notes.get(self.month_str, "")
                        self.notes_input.setPlainText(notes)
                        
                        print(f"[ADJUSTMENT] Ajuste existente cargado:  {adjustment_amount}")
                    
                    break

        except Exception as e:
            print(f"[ADJUSTMENT] Error cargando ajuste existente: {e}")
            import traceback
            traceback. print_exc()

    def _calculate_difference(self):
        """Calcula la diferencia entre utilidad real y calculada."""
        try:
            real_str = self.real_input.text().strip().replace(",", "")
            if not real_str: 
                self.diff_value.setText("RD$ 0.00")
                self.diff_value.setStyleSheet("font-size: 15px; font-weight: 700; color:  #64748B;")
                return

            real_profit = float(real_str)
            difference = self.calculated_profit - real_profit

            # Color según el signo
            if difference > 0:
                # Utilidad calculada es mayor → necesitamos agregar un gasto (rojo)
                color = "#DC2626"
                sign = "+"
            elif difference < 0:
                # Utilidad calculada es menor → necesitamos restar un gasto / agregar ingreso (verde)
                color = "#15803D"
                sign = ""
            else:
                color = "#64748B"
                sign = ""

            self.diff_value. setText(f"{sign}RD$ {abs(difference):,.2f}")
            self.diff_value.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {color};")

        except ValueError:
            self.diff_value.setText("RD$ 0.00")
            self.diff_value.setStyleSheet("font-size: 15px; font-weight: 700; color:  #64748B;")

    def _save_adjustment(self):
        """Guarda el ajuste como gasto adicional ACUMULATIVO."""
        try:
            real_str = self.real_input.text().strip().replace(",", "")
            if not real_str:
                QMessageBox.warning(
                    self,
                    "Validación",
                    "Debe ingresar la utilidad real según su contabilidad."
                )
                self.real_input.setFocus()
                return

            real_profit = float(real_str)
            difference = self.calculated_profit - real_profit

            if abs(difference) < 0.01:
                QMessageBox.information(
                    self,
                    "Sin Diferencia",
                    "La utilidad calculada coincide con la utilidad real.\n"
                    "No es necesario realizar ajuste."
                )
                return

            # Confirmar con el usuario
            diff_sign = "+" if difference > 0 else ""
            reply = QMessageBox.question(
                self,
                "Confirmar Ajuste",
                f"Se creará/actualizará un ajuste de:\n\n"
                f"Utilidad Calculada: RD$ {self.calculated_profit:,.2f}\n"
                f"Utilidad Real: RD$ {real_profit:,.2f}\n"
                f"Diferencia: {diff_sign}RD$ {difference:,.2f}\n\n"
                f"¿Desea continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox. StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # ✅ NUEVO:   Usar sistema acumulativo anual
            notes = self.notes_input.toPlainText().strip() or \
                    f"Ajuste para igualar utilidad real (RD$ {real_profit: ,.2f}) " \
                    f"con utilidad calculada (RD$ {self.calculated_profit:,.2f})"

            print(f"[ADJUSTMENT] Guardando ajuste acumulativo...")
            print(f"[ADJUSTMENT] Company: {self.company_id}")
            print(f"[ADJUSTMENT] Periodo: {self.month_str}/{self.year_int}")
            print(f"[ADJUSTMENT] Diferencia: {difference}")

            if hasattr(self.controller, "update_annual_expense_value"):
                ok, msg = self.controller.update_annual_expense_value(
                    company_id=self.company_id,
                    year=self.year_int,
                    month_str=self.month_str,
                    concept_name="AJUSTE CONTABLE",
                    category="Ajuste Contable",
                    value=difference,  # Positivo = gasto, Negativo = reducción
                    note=notes
                )

                if ok:
                    QMessageBox.information(self, "Éxito", "Ajuste guardado correctamente.")
                    print(f"[ADJUSTMENT] ✅ Ajuste guardado exitosamente")
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", msg)
                    print(f"[ADJUSTMENT] ❌ Error:  {msg}")
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Método update_annual_expense_value no implementado en el controller."
                )
                print(f"[ADJUSTMENT] ❌ Método no existe en controller")

        except ValueError: 
            QMessageBox.warning(
                self,
                "Error",
                "El valor de utilidad real debe ser un número válido."
            )
        except Exception as e:
            print(f"[ADJUSTMENT] ❌ Excepción: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Error",
                f"Error al guardar el ajuste:\n{e}"
            )