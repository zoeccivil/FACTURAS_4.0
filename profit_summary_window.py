from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QComboBox,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QDate


def show_styled_message(parent, icon_type, title, message):
    """Muestra un QMessageBox con estilos del tema moderno."""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    
    if icon_type == "warning":
        msg.setIcon(QMessageBox.Icon.Warning)
    elif icon_type == "error":
        msg.setIcon(QMessageBox. Icon.Critical)
    elif icon_type == "info":
        msg.setIcon(QMessageBox.Icon.Information)
    elif icon_type == "question": 
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setStandardButtons(
            QMessageBox.StandardButton. Yes | QMessageBox.StandardButton. No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.No)
    
    msg.setStyleSheet("""
        QMessageBox {
            background-color: #FFFFFF;
        }
        QMessageBox QLabel {
            color: #1E293B;
            font-size: 13px;
            min-width: 300px;
        }
        QPushButton {
            background-color: #3B82F6;
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            padding: 8px 20px;
            font-weight: 600;
            font-size: 13px;
            min-width: 80px;
        }
        QPushButton:hover {
            background-color: #2563EB;
        }
        QPushButton:pressed {
            background-color: #1D4ED8;
        }
    """)
    
    return msg. exec() if icon_type == "question" else msg.exec()




class ProfitSummaryWindow(QDialog):
    """
    Ventana de Resumen de Utilidades - DISEÑO MEJORADO con Ajustes.  
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
        month_str:  str = None,
        year_int: int = None,
    ):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.company_id = company_id
        self. company_name = company_name
        
        if not month_str:
            month_str = f"{QDate.currentDate().month():02d}"
        if not year_int:
            year_int = QDate.currentDate().year()
            
        self.current_month_str = month_str
        self.current_year_int = year_int
        self.report_data = None

        self.setWindowTitle(f"Resumen de Utilidades - {company_name}")
        self.resize(840, 480)
        self.setModal(True)

        self._build_ui()
        self._load_period_into_filters(month_str, year_int)
        self._load_data()

    def _build_ui(self):
            root = QVBoxLayout(self)
            root.setContentsMargins(20, 20, 20, 20)
            root.setSpacing(16)

            # === HEADER CON FILTROS ===
            header_card = QFrame()
            header_card.setObjectName("headerCard")
            header_layout = QVBoxLayout(header_card)
            header_layout.setContentsMargins(20, 16, 20, 16)
            header_layout.setSpacing(12)

            top_row = QHBoxLayout()
            top_row.setSpacing(12)

            title_section = QVBoxLayout()
            title_section.setSpacing(2)
            
            title = QLabel("💰 Resumen de Utilidades")
            title.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A;")
            
            self.subtitle_label = QLabel(f"{self.company_name}")
            self.subtitle_label.setStyleSheet("font-size: 12px; color: #64748B;")
            
            title_section.addWidget(title)
            title_section.addWidget(self.subtitle_label)
            
            top_row.addLayout(title_section)
            top_row.addStretch()

            filter_container = QHBoxLayout()
            filter_container.setSpacing(8)
            
            lbl_mes = QLabel("Mes:")
            lbl_mes.setStyleSheet("color: #475569; font-weight: 600; font-size: 13px;")
            
            self.month_selector = QComboBox()
            self.month_selector.setObjectName("modernCombo")
            for m in self.MONTHS_MAP.keys():
                self.month_selector.addItem(m)
            self.month_selector.currentIndexChanged.connect(self._on_period_changed)
            self.month_selector.setMinimumWidth(130)

            lbl_ano = QLabel("Año:")
            lbl_ano.setStyleSheet("color: #475569; font-weight: 600; font-size: 13px;")
            
            self.year_selector = QComboBox()
            self.year_selector.setObjectName("modernCombo")
            self.year_selector.currentIndexChanged.connect(self._on_period_changed)
            self.year_selector.setMinimumWidth(100)

            filter_container.addWidget(lbl_mes)
            filter_container.addWidget(self.month_selector)
            filter_container.addSpacing(8)
            filter_container.addWidget(lbl_ano)
            filter_container.addWidget(self.year_selector)
            
            top_row.addLayout(filter_container)
            header_layout.addLayout(top_row)

            root.addWidget(header_card)

            # === CARDS DE MÉTRICAS ===
            metrics_card = QFrame()
            metrics_card.setObjectName("metricsCard")
            metrics_layout = QHBoxLayout(metrics_card)
            metrics_layout.setContentsMargins(20, 20, 20, 20)
            metrics_layout.setSpacing(16)

            income_fac_card = self._create_metric_card("Ingresos Facturados", "#15803D", "#ECFDF5")
            self.label_total_ingresos = income_fac_card["value_label"]
            metrics_layout.addWidget(income_fac_card["widget"], 1)

            # ✅ NUEVO: Card de Ingresos Adicionales (Verde)
            income_add_card = self._create_metric_card("Ingresos Adicionales", "#16A34A", "#F0FDF4")
            self.label_ingresos_adicionales = income_add_card["value_label"]
            metrics_layout.addWidget(income_add_card["widget"], 1)

            expense_fac_card = self._create_metric_card("Gastos Facturados", "#DC2626", "#FEF2F2")
            self.label_gastos_facturados = expense_fac_card["value_label"]
            metrics_layout.addWidget(expense_fac_card["widget"], 1)

            expense_add_card = self._create_metric_card("Gastos Adicionales", "#EA580C", "#FFF7ED")
            self.label_gastos_adicionales = expense_add_card["value_label"]
            metrics_layout.addWidget(expense_add_card["widget"], 1)

            root.addWidget(metrics_card)

            # === UTILIDAD NETA ===
            result_card = QFrame()
            result_card.setObjectName("resultCard")
            result_layout = QHBoxLayout(result_card)
            result_layout.setContentsMargins(24, 20, 24, 20)
            result_layout.setSpacing(16)

            result_label = QLabel("UTILIDAD NETA:")
            result_label.setStyleSheet(
                "font-size: 16px; font-weight: 700; color: #1E293B; letter-spacing: 0.5px;"
            )

            self.label_utilidad_neta = QLabel("RD$ 0.00")
            self.label_utilidad_neta.setStyleSheet(
                "font-size: 28px; font-weight: 800; color: #1D4ED8;"
            )

            result_layout.addWidget(result_label)
            result_layout.addWidget(self.label_utilidad_neta)
            result_layout.addStretch()

            root.addWidget(result_card)

            # === BOTONES (LAYOUT CORREGIDO) ===
            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(16)
            btn_layout.setContentsMargins(0, 10, 0, 0)
            
            # ✅ NUEVO: Botón de Ingresos Adicionales (Verde)
            self.btn_gestionar_ingresos = QPushButton("📈 Gestionar Ingresos Adicionales")
            self.btn_gestionar_ingresos.setObjectName("incomeButton")
            self.btn_gestionar_ingresos.clicked.connect(self._open_additional_income_manager)
            
            self.btn_gestionar_gastos = QPushButton("⚙️ Gestionar Gastos Adicionales")
            self.btn_gestionar_gastos.setObjectName("secondaryButton")
            self.btn_gestionar_gastos.clicked.connect(self._open_additional_expenses_manager)
            
            self.btn_ajustar_utilidad = QPushButton("⚖️ Ajustar Utilidad")
            self.btn_ajustar_utilidad.setObjectName("adjustButton")
            self.btn_ajustar_utilidad.clicked.connect(self._open_profit_adjustment)
            
            self.btn_generar_reporte = QPushButton("📄 Generar Reporte PDF")
            self.btn_generar_reporte.setObjectName("primaryButton")
            self.btn_generar_reporte.clicked.connect(self._generate_pdf_report)
            
            btn_layout.addStretch() 
            btn_layout.addWidget(self.btn_gestionar_ingresos)
            btn_layout.addWidget(self.btn_gestionar_gastos)
            btn_layout.addWidget(self.btn_ajustar_utilidad)
            btn_layout.addWidget(self.btn_generar_reporte)
            btn_layout.addStretch()
            
            root.addLayout(btn_layout)
            # root.addStretch() # Eliminamos este stretch final para que los botones queden bien asentados abajo

            # === ESTILOS (CORREGIDOS Y UNIFICADOS) ===
            self.setStyleSheet("""
                QDialog {
                    background-color: #F8F9FA;
                }

                /* === ARREGLO PARA QMESSAGEBOX (ALERTAS) === */
                QMessageBox {
                    background-color: #FFFFFF; /* Fondo blanco explícito */
                }
                QMessageBox QLabel {
                    color: #0F172A; /* Texto NEGRO oscuro para que se lea */
                    font-size: 13px;
                    font-weight: 500;
                    background-color: transparent;
                }
                QMessageBox QPushButton {
                    background-color: #1E293B;
                    color: #FFFFFF;
                    border-radius: 6px;
                    padding: 6px 16px;
                    min-width: 80px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #334155;
                }
                
                /* === CARDS === */
                QFrame#headerCard, QFrame#metricsCard {
                    background-color: #FFFFFF;
                    border-radius: 12px;
                    border: 1px solid #E5E7EB;
                }
                
                QFrame#resultCard {
                    background-color: #FFFFFF;
                    border-radius: 12px;
                    border: 2px solid #3B82F6;
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 #EFF6FF, 
                        stop:1 #FFFFFF
                    );
                }
                
                QFrame.metricCard {
                    background-color: white;
                    border-radius: 10px;
                    border: 2px solid;
                    padding: 16px;
                }
                
                /* === COMBOBOX === */
                QComboBox#modernCombo {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 6px 12px;
                    color: #0F172A;
                    font-size: 13px;
                    font-weight: 500;
                }
                QComboBox#modernCombo:hover { border-color: #3B82F6; }
                QComboBox#modernCombo:focus { border-color: #2563EB; border-width: 2px; }
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
                
                /* === BOTONES UNIFORMES (CORREGIDO) === */
                /* Se aplica 'height: 40px' a todos para alineación perfecta */
                
                QPushButton#primaryButton {
                    background-color: #1E293B;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    padding: 0px 24px; /* Padding lateral solo */
                    font-weight: 600;
                    font-size: 14px;
                    min-width: 200px;
                    height: 40px; /* ALTO FIJO PARA ALINEACIÓN */
                }
                QPushButton#primaryButton:hover { background-color: #0F172A; }
                QPushButton#primaryButton:pressed { background-color: #020617; }
                
                QPushButton#secondaryButton {
                    background-color: #64748B;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    padding: 0px 24px;
                    font-weight: 600;
                    font-size: 14px;
                    min-width: 200px;
                    height: 40px; /* ALTO FIJO PARA ALINEACIÓN */
                }
                QPushButton#secondaryButton:hover { background-color: #475569; }
                QPushButton#secondaryButton:pressed { background-color: #334155; }
                
                QPushButton#adjustButton {
                    background-color: #EA580C;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    padding: 0px 24px;
                    font-weight: 600;
                    font-size: 14px;
                    min-width: 200px;
                    height: 40px; /* ALTO FIJO PARA ALINEACIÓN */
                }
                QPushButton#adjustButton:hover { background-color: #C2410C; }
                QPushButton#adjustButton:pressed { background-color: #9A3412; }
                
                QPushButton#incomeButton {
                    background-color: #15803D;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    padding: 0px 24px;
                    font-weight: 600;
                    font-size: 14px;
                    min-width: 200px;
                    height: 40px; /* ALTO FIJO PARA ALINEACIÓN */
                }
                QPushButton#incomeButton:hover { background-color: #166534; }
                QPushButton#incomeButton:pressed { background-color: #14532D; }
            """)

    def _create_metric_card(self, title: str, color:  str, bg_color: str):
        """Crea una card de métrica."""
        widget = QFrame()
        widget.setObjectName("metricCard")
        widget.setProperty("class", "metricCard")
        widget.setStyleSheet(f"""
            QFrame#metricCard {{
                border-color: {color};
                background-color: {bg_color};
            }}
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: #64748B; font-size: 12px; font-weight: 600; "
            f"text-transform: uppercase; letter-spacing: 0.5px;"
        )
        layout.addWidget(title_lbl)
        
        value_lbl = QLabel("RD$ 0.00")
        value_lbl.setStyleSheet(
            f"color: {color}; font-size: 22px; font-weight: 800;"
        )
        layout.addWidget(value_lbl)
        layout.addStretch()
        
        return {"widget": widget, "value_label": value_lbl}

    def _load_period_into_filters(self, month_str:  str, year_int: int):
        """Configura los combos."""
        month_name = "Todos"
        for name, code in self.MONTHS_MAP. items():
            if code == month_str:
                month_name = name
                break
        
        if month_name in self.MONTHS_MAP: 
            idx = list(self.MONTHS_MAP. keys()).index(month_name)
            self.month_selector. setCurrentIndex(idx)
        else:
            self.month_selector.setCurrentIndex(0)

        self.year_selector.clear()
        base_year = year_int or QDate.currentDate().year()
        years = sorted({base_year - 1, base_year, base_year + 1})
        for y in years:
            self.year_selector.addItem(str(y))
        
        try:
            idx_y = years.index(base_year)
            self.year_selector.setCurrentIndex(idx_y)
        except ValueError: 
            self.year_selector. setCurrentIndex(1 if len(years) > 1 else 0)

        self._update_subtitle()

    def _update_subtitle(self):
        """Actualiza el subtítulo."""
        month_name = self.month_selector.currentText()
        try:
            year_val = int(self.year_selector.currentText())
        except: 
            year_val = self.current_year_int
        
        if month_name == "Todos":
            period_str = f"Año {year_val}"
        else:
            period_str = f"{month_name} {year_val}"
        
        self. subtitle_label.setText(f"{self.company_name} – {period_str}")

    def _load_data(self):
        """Carga datos desde el controller."""
        month_name = self.month_selector.currentText()
        self.current_month_str = self.MONTHS_MAP.get(month_name)
        try:
            self.current_year_int = int(self.year_selector.currentText())
        except:
            self.current_year_int = QDate.currentDate().year()

        summary = {}
        try:
            if hasattr(self.controller, "get_profit_summary"):
                summary = self.controller.get_profit_summary(
                    self.company_id,
                    self.current_month_str,
                    self.current_year_int
                ) or {}
        except Exception as e: 
            print(f"[PROFIT] Error: {e}")
            QMessageBox.warning(self, "Error", f"Error cargando datos:\n{e}")
            summary = {}

        self.report_data = summary

        total_ingresos_fac = float(summary.get("total_income", 0.0))
        ingresos_adicionales = float(summary.get("additional_income", 0.0))  # ✅ NUEVO
        gastos_facturados = float(summary.get("total_expense", 0.0))
        gastos_adicionales = float(summary.get("additional_expenses", 0.0))
        utilidad_neta = float(summary.get("net_profit", 0.0))

        self.label_total_ingresos.setText(f"RD$ {total_ingresos_fac:,.2f}")
        self.label_ingresos_adicionales.setText(f"RD$ {ingresos_adicionales:,.2f}")  # ✅ NUEVO
        self.label_gastos_facturados.setText(f"RD$ {gastos_facturados:,.2f}")
        self.label_gastos_adicionales.setText(f"RD$ {gastos_adicionales:,.2f}")
        
        if utilidad_neta >= 0:
            color = "#15803D"
            prefix = "✅ "
        else:
            color = "#DC2626"
            prefix = "⚠️ "
        
        self.label_utilidad_neta.setStyleSheet(
            f"font-size: 28px; font-weight: 800; color: {color};"
        )
        self.label_utilidad_neta.setText(f"{prefix}RD$ {utilidad_neta:,.2f}")



    def _on_period_changed(self):
        """Evento de cambio de periodo."""
        self._update_subtitle()
        self._load_data()

    def _open_additional_income_manager(self):
        """Abre gestor de ingresos adicionales ACUMULATIVOS."""
        try:
            from annual_income_manager import AnnualIncomeManager
            
            dlg = AnnualIncomeManager(
                parent=self,
                controller=self.controller,
                company_id=self.company_id,
                company_name=self.company_name,
                month_str=self.current_month_str or "01",
                year_int=self.current_year_int
            )
            dlg.exec()
            self._load_data()  # Refrescar datos después de cerrar
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error abriendo gestor de ingresos:\n{str(e)}")

    def _open_additional_expenses_manager(self):
        """Abre gestor de gastos adicionales ACUMULATIVOS."""
        try:
            from annual_expenses_manager import AnnualExpensesManager
            
            dlg = AnnualExpensesManager(
                parent=self,
                controller=self.controller,
                company_id=self.company_id,
                company_name=self.company_name,
                month_str=self.current_month_str or "01",
                year_int=self.current_year_int,
            )
            dlg.exec()
            self._load_data()
            
        except ImportError as e:
            show_styled_message(self, "error", "Error", f"No se pudo cargar el gestor:\n{e}")

    def _open_profit_adjustment(self):
        """Abre el diálogo de ajuste manual de utilidad."""
        if not self.report_data:
            QMessageBox.warning(self, "Sin Datos", "Primero cargue los datos del periodo.")
            return

        if not self.current_month_str: 
            QMessageBox.warning(
                self,
                "Ajuste no disponible",
                "El ajuste de utilidad solo está disponible para periodos mensuales.\n"
                "Seleccione un mes específico."
            )
            return

        try:
            from profit_adjustment_dialog import ProfitAdjustmentDialog
            
            calculated_profit = float(self.report_data.get("net_profit", 0.0))
            
            dlg = ProfitAdjustmentDialog(
                parent=self,
                controller=self.controller,
                company_id=self.company_id,
                company_name=self.company_name,
                month_str=self.current_month_str,
                year_int=self.current_year_int,
                calculated_profit=calculated_profit,
            )
            
            if dlg.exec():
                self._load_data()
                
        except ImportError as e: 
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo cargar el diálogo de ajuste:\n{e}"
            )

    def _generate_pdf_report(self):
        """Genera reporte PDF de utilidades."""
        if not self.report_data:
            show_styled_message(self, "warning", "Sin Datos", "No hay datos para generar reporte.")
            return

        month_name = self.month_selector.currentText()
        year_str = self.year_selector.currentText()

        if month_name == "Todos":
            filename_suggestion = f"Reporte_Utilidades_{self.company_name. replace(' ', '_')}_{year_str}.pdf"
        else:
            filename_suggestion = f"Reporte_Utilidades_{self.company_name.replace(' ', '_')}_{month_name}_{year_str}.pdf"

        fname, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Reporte de Utilidades",
            filename_suggestion,
            "PDF Files (*.pdf)",
        )
        
        if not fname:
            return

        try:
            import report_generator
            
            # ✅ NUEVO: Obtener conceptos anuales en lugar de gastos individuales
            additional_expenses = []
            try:
                if hasattr(self. controller, "get_annual_expense_concepts"):
                    additional_expenses = self.controller.get_annual_expense_concepts(
                        self.company_id,
                        self.current_year_int
                    ) or []
            except Exception as e:
                print(f"[PROFIT-PDF] Error obteniendo conceptos anuales: {e}")

            report_data = {
                "summary": self.report_data,
                "additional_expenses": additional_expenses,  # ✅ Ahora son conceptos anuales
                "company_name": self.company_name,
                "period": f"{month_name} {year_str}" if month_name != "Todos" else f"Año {year_str}",
                "month":  month_name,
                "month_str": self.current_month_str,  # ✅ NUEVO
                "year": year_str,
            }

            ok, msg = report_generator.generate_profit_report_pdf(report_data, fname)
            
            if ok:
                show_styled_message(self, "info", "Éxito", msg)
            else:
                show_styled_message(self, "error", "Error", msg)

        except Exception as e:
            show_styled_message(self, "error", "Error", f"Error generando PDF:\n{e}")