from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QWidget,
    QMessageBox,
    QFrame,
    QMenu,
    QFileDialog,
    QScrollArea,
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont, QColor
from datetime import datetime
import os

try:
    from advanced_retention_window_qt import AdvancedRetentionWindowQt
except Exception:
    AdvancedRetentionWindowQt = None  # placeholder si aún no está migrada

try:
    from tax_payments_manager import TaxPaymentManager
    from tax_payment_report_generator import TaxPaymentReportGenerator
except Exception:
    TaxPaymentManager = None
    TaxPaymentReportGenerator = None


class TaxCalculationManagementWindowQt(QDialog):
    """
    Ventana moderna para gestionar cálculos de impuestos guardados.

    Espera que el controller implemente (en modo real o placeholder):
      - get_tax_calculations(company_id) -> lista de dicts
      - delete_tax_calculation(calc_id) -> (bool, mensaje)
      - open_tax_calculation_pdf(calc_id, parent) -> genera/abre PDF

    Para crear/editar usa AdvancedRetentionWindowQt si está disponible.
    """

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        
        # Almacenar datos para reportes
        self.calculations = []
        self.company_name = ""

        self.setWindowTitle("Gestión de Cálculos de Impuestos")
        self.resize(980, 650)
        self.setModal(True)

        self._build_ui()
        self._load_calculations()

    # ------------------------------------------------------------------ #
    # UI
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        card = QFrame()
        card.setObjectName("taxCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(12)

        # ====== ENCABEZADO ======
        header = QHBoxLayout()
        title = QLabel("Cálculos de Impuestos Guardados")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #0F172A;")
        subtitle = QLabel(
            "Administra impuestos, marca pagos y genera reportes mensuales."
        )
        subtitle.setStyleSheet("font-size: 12px; color: #6B7280;")
        subtitle.setWordWrap(True)

        header.addWidget(title)
        header.addStretch()
        card_layout.addLayout(header)
        card_layout.addWidget(subtitle)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        card_layout.addWidget(line)

        # ====== PANEL DE RESUMEN ======
        summary_frame = QFrame()
        summary_frame.setObjectName("summaryFrame")
        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(12)

        # Crear tarjetas de resumen
        self.total_label = self._create_summary_card("Total", "0", "0")
        self.paid_label = self._create_summary_card("✓ Pagados", "0", "0")
        self.pending_label = self._create_summary_card("⧗ Pendientes", "0", "0")
        self.percentage_label = self._create_summary_card("% Pagado", "0%", "")

        summary_layout.addWidget(self.total_label)
        summary_layout.addWidget(self.paid_label)
        summary_layout.addWidget(self.pending_label)
        summary_layout.addWidget(self.percentage_label)

        card_layout.addWidget(summary_frame)

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        card_layout.addWidget(line2)

        # ====== TABLA DE CÁLCULOS ======
        list_frame = QWidget()
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(6)

        table_label = QLabel("Cálculos Guardados")
        table_label.setStyleSheet("font-weight: 600; color: #4B5563; font-size: 13px;")
        list_layout.addWidget(table_label)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Nombre del Cálculo", "Fecha de Creación", "Estado"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._open_context_menu)
        list_layout.addWidget(self.table)

        card_layout.addWidget(list_frame)

        # ====== BOTONES ======
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 8, 0, 0)
        btn_row.setSpacing(8)

        btn_new = QPushButton("Nuevo Cálculo")
        btn_new.setObjectName("primaryButton")
        btn_new.clicked.connect(self._new)

        btn_edit = QPushButton("Editar Selección")
        btn_edit.setObjectName("secondaryButton")
        btn_edit.clicked.connect(self._edit)

        btn_export = QPushButton("Generar PDF")
        btn_export.setObjectName("secondaryButton")
        btn_export.clicked.connect(self._export)

        btn_report = QPushButton("Generar Reporte Completo")
        btn_report.setObjectName("successButton")
        btn_report.clicked.connect(self._generate_full_report)

        btn_delete = QPushButton("Eliminar")
        btn_delete.setObjectName("dangerButton")
        btn_delete.clicked.connect(self._delete)

        btn_close = QPushButton("Cerrar")
        btn_close.setObjectName("secondaryButton")
        btn_close.clicked.connect(self.reject)

        btn_row.addWidget(btn_new)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_export)
        btn_row.addWidget(btn_report)
        btn_row.addStretch()
        btn_row.addWidget(btn_delete)
        btn_row.addWidget(btn_close)

        card_layout.addLayout(btn_row)
        root.addWidget(card)

        # ====== ESTILOS ======
        self.setStyleSheet(
            self.styleSheet()
            + """
        QFrame#taxCard {
            background-color: #FFFFFF;
            border-radius: 12px;
            border: 1px solid #E2E8F0;
        }
        QFrame#summaryFrame {
            background-color: #F9FAFB;
            border-radius: 8px;
            border: 1px solid #E2E8F0;
            padding: 8px;
        }
        QFrame#summaryCard {
            background-color: #FFFFFF;
            border-radius: 6px;
            border: 1px solid #E2E8F0;
            padding: 8px;
        }
        QLabel#summaryTitle {
            font-size: 12px;
            color: #6B7280;
            font-weight: 500;
        }
        QLabel#summaryValue {
            font-size: 18px;
            color: #0F172A;
            font-weight: 700;
        }
        QLabel#summarySubtitle {
            font-size: 10px;
            color: #A0AEC0;
        }
        QPushButton#primaryButton {
            background-color: #1E293B;
            color: #FFFFFF;
            padding: 6px 14px;
            border-radius: 6px;
            font-weight: 500;
            border: none;
        }
        QPushButton#primaryButton:hover {
            background-color: #0F172A;
        }
        QPushButton#secondaryButton {
            background-color: #F9FAFB;
            color: #374151;
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid #D1D5DB;
            font-weight: 500;
        }
        QPushButton#secondaryButton:hover {
            background-color: #E5E7EB;
        }
        QPushButton#successButton {
            background-color: #F0FDF4;
            color: #166534;
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid #BBEF63;
            font-weight: 500;
        }
        QPushButton#successButton:hover {
            background-color: #DCFCE7;
        }
        QPushButton#dangerButton {
            background-color: #FEF2F2;
            color: #B91C1C;
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid #FECACA;
            font-weight: 500;
        }
        QPushButton#dangerButton:hover {
            background-color: #FEE2E2;
        }
        """
        )

    def _create_summary_card(self, title: str, value: str, subtitle: str) -> QFrame:
        """Crea una tarjeta de resumen."""
        card = QFrame()
        card.setObjectName("summaryCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setObjectName("summaryTitle")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setObjectName("summaryValue")
        layout.addWidget(value_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("summarySubtitle")
            layout.addWidget(subtitle_label)

        return card

    # ------------------------------------------------------------------ #
    # Carga de datos
    # ------------------------------------------------------------------ #
    def _load_calculations(self):
        self.table.setRowCount(0)
        self.calculations = []

        company_id = None
        try:
            if self.parent and hasattr(self.parent, "get_current_company_id"):
                company_id = self.parent.get_current_company_id()
                # Intentar obtener nombre de empresa
                if hasattr(self.parent, "get_current_company_name"):
                    self.company_name = self.parent.get_current_company_name() or ""
        except Exception:
            company_id = None

        try:
            if hasattr(self.controller, "get_tax_calculations"):
                calculations = self.controller.get_tax_calculations(company_id) or []
            else:
                calculations = []
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron obtener los cálculos: {e}")
            calculations = []

        normalized = []
        for c in calculations:
            try:
                normalized.append(dict(c))
            except Exception:
                if isinstance(c, dict):
                    normalized.append(c)
                else:
                    try:
                        normalized.append({k: c[k] for k in c.keys()})
                    except Exception:
                        normalized.append(c)
        
        self.calculations = normalized

        for calc in normalized:
            row = self.table.rowCount()
            self.table.insertRow(row)

            name = str(calc.get("name") or calc.get("title") or "")
            name_item = QTableWidgetItem(name)
            name_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            name_item.setData(Qt.ItemDataRole.UserRole, calc.get("id"))

            date_raw = calc.get("creation_date") or calc.get("created_at") or ""
            date_str = self._format_date(date_raw)
            date_item = QTableWidgetItem(date_str)
            date_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)

            is_paid = bool(calc.get("is_paid", False))
            status_item = QTableWidgetItem()
            status_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            status_item.setCheckState(
                Qt.CheckState.Checked if is_paid else Qt.CheckState.Unchecked
            )
            status_item.setText("✓ Pagado" if is_paid else "⧗ Pendiente")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, date_item)
            self.table.setItem(row, 2, status_item)
        
        # Conectar señal para detectar cambios en el checkbox
        self.table.cellClicked.connect(self._on_cell_clicked)
        
        # Recalcular totales para cálculos que no tienen monto (migración)
        self._recalculate_missing_totals()
        
        # Actualizar panel de resumen
        self._update_summary()

    def _update_summary(self):
        """Actualiza el panel de resumen con datos de pagos."""
        if TaxPaymentManager is None:
            return
        
        summary = TaxPaymentManager.calculate_payment_summary(self.calculations)
        
        total_text = TaxPaymentManager.format_currency(summary.get("total_amount", 0))
        paid_text = TaxPaymentManager.format_currency(summary.get("paid_amount", 0))
        pending_text = TaxPaymentManager.format_currency(summary.get("pending_amount", 0))
        percentage_text = f"{summary.get('paid_percentage', 0)}%"
        
        # Actualizar labels (usar find para obtener el label dentro del card)
        self._update_summary_card_value(self.total_label, total_text)
        self._update_summary_card_value(self.paid_label, paid_text)
        self._update_summary_card_value(self.pending_label, pending_text)
        self._update_summary_card_value(self.percentage_label, percentage_text)

    def _update_summary_card_value(self, card: QFrame, value: str):
        """Actualiza el valor de una tarjeta de resumen."""
        for child in card.findChildren(QLabel):
            if child.objectName() == "summaryValue":
                child.setText(value)
                break

    def _recalculate_missing_totals(self):
        """Recalcula totales para cálculos que no tienen monto guardado (migración)."""
        if not hasattr(self.controller, "recalculate_tax_calculation_totals"):
            return
        
        try:
            # Buscar cálculos sin monto o con monto 0
            for i, calc in enumerate(self.calculations):
                calc_id = calc.get("id")
                total_amount = float(calc.get("total_amount") or 0)
                
                if total_amount == 0 and calc_id:
                    # Recalcular desde los detalles
                    success, new_total, msg = self.controller.recalculate_tax_calculation_totals(calc_id)
                    if success:
                        self.calculations[i]["total_amount"] = new_total
                        print(f"[DEBUG] Recalculado {calc.get('name')}: RD$ {new_total:,.2f}")
        except Exception as e:
            print(f"[DEBUG] Error en recalculate_missing_totals: {e}")

    def _on_cell_clicked(self, row, column):
        """Maneja el click en las celdas, especialmente para la columna de estado."""
        if column == 2:  # Columna "Estado"
            status_item = self.table.item(row, 2)
            if not status_item:
                return
            
            # Obtener el ID del cálculo
            name_item = self.table.item(row, 0)
            if not name_item:
                return
            calc_id = name_item.data(Qt.ItemDataRole.UserRole)
            
            # Toggle el estado
            new_state = status_item.checkState() == Qt.CheckState.Checked
            
            # Actualizar el texto visual
            status_item.setText("✓ Pagado" if new_state else "⧗ Pendiente")
            
            # Actualizar en la base de datos
            try:
                if hasattr(self.controller, "update_tax_calculation_paid_status"):
                    success, msg = self.controller.update_tax_calculation_paid_status(calc_id, new_state)
                    if not success:
                        QMessageBox.warning(self, "Error", f"No se pudo actualizar el estado: {msg}")
                        # Revertir el cambio visual
                        status_item.setCheckState(
                            Qt.CheckState.Unchecked if new_state else Qt.CheckState.Checked
                        )
                        status_item.setText("⧗ Pendiente" if new_state else "✓ Pagado")
                    else:
                        # Actualizar dato local y resumen
                        if calc_id:
                            for calc in self.calculations:
                                if calc.get("id") == calc_id or str(calc.get("id")) == str(calc_id):
                                    calc["is_paid"] = new_state
                                    break
                        self._update_summary()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Error al actualizar estado: {e}")

    def _format_date(self, value) -> str:
        if not value:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M")
        try:
            s = str(value)
            if len(s) >= 10:
                return s[:16]
            return s
        except Exception:
            return str(value)

    def _get_selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if not item:
            return None
        val = item.data(Qt.ItemDataRole.UserRole)
        try:
            return int(val)
        except Exception:
            return val

    # ------------------------------------------------------------------ #
    # Acciones
    # ------------------------------------------------------------------ #
    def _new(self):
        if AdvancedRetentionWindowQt is None:
            QMessageBox.information(
                self,
                "No disponible",
                "La ventana avanzada de cálculo de retenciones aún no está disponible.",
            )
            return
        try:
            dlg = AdvancedRetentionWindowQt(self.parent, self.controller, calculation_id=None)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self._load_calculations()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir la ventana de cálculo: {e}")

    def _edit(self):
        calc_id = self._get_selected_id()
        if not calc_id:
            QMessageBox.warning(self, "Sin selección", "Por favor, selecciona un cálculo para editar.")
            return

        if AdvancedRetentionWindowQt is None:
            QMessageBox.information(
                self,
                "No disponible",
                "La ventana avanzada de cálculo de retenciones aún no está disponible.",
            )
            return

        try:
            dlg = AdvancedRetentionWindowQt(self.parent, self.controller, calculation_id=calc_id)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self._load_calculations()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir la ventana de edición: {e}")

    def _delete(self):
        calc_id = self._get_selected_id()
        if not calc_id:
            QMessageBox.warning(self, "Sin selección", "Por favor, selecciona un cálculo para eliminar.")
            return

        resp = QMessageBox.question(
            self,
            "Confirmar",
            "¿Estás seguro de que deseas eliminar este cálculo guardado?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        try:
            if hasattr(self.controller, "delete_tax_calculation"):
                success, message = self.controller.delete_tax_calculation(calc_id)
            else:
                success, message = False, "El controlador no implementa delete_tax_calculation."

            if success:
                QMessageBox.information(self, "Éxito", message)
                self._load_calculations()  # Recarga y actualiza resumen
            else:
                QMessageBox.critical(self, "Error", message)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo eliminar el cálculo: {e}")

    def _export(self):
        """Generar/abrir PDF del cálculo seleccionado sin entrar a editar."""
        calc_id = self._get_selected_id()
        if not calc_id:
            QMessageBox.warning(self, "Sin selección", "Selecciona un cálculo para exportar.")
            return

        if not hasattr(self.controller, "open_tax_calculation_pdf"):
            QMessageBox.warning(
                self,
                "No disponible",
                "El controlador no implementa 'open_tax_calculation_pdf'.",
            )
            return

        try:
            self.controller.open_tax_calculation_pdf(calc_id, parent=self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar el PDF: {e}")

    def _generate_full_report(self):
        """Genera reporte PDF completo con todos los impuestos, pagados y pendientes, organizados por mes."""
        if not self.calculations:
            QMessageBox.information(
                self,
                "Sin datos",
                "No hay cálculos para generar el reporte.",
            )
            return

        if TaxPaymentManager is None or TaxPaymentReportGenerator is None:
            QMessageBox.critical(
                self,
                "No disponible",
                "Las dependencias requeridas para generar reportes no están disponibles.",
            )
            return

        try:
            # Seleccionar ubicación para guardar PDF
            default_filename = f"Reporte_Impuestos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Reporte de Pagos de Impuestos",
                default_filename,
                "Archivos PDF (*.pdf);;Todos los archivos (*)",
            )

            if not file_path:
                return

            # Generar datos del reporte
            report_data = TaxPaymentManager.generate_monthly_report_data(
                self.calculations,
                self.company_name,
                include_details=True
            )

            # Generar PDF
            generator = TaxPaymentReportGenerator(self.company_name)
            success, message = generator.generate_pdf(report_data, file_path)

            if success:
                msg = f"{message}\n\n¿Deseas abrir el reporte ahora?"
                resp = QMessageBox.question(
                    self,
                    "Éxito",
                    msg,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if resp == QMessageBox.StandardButton.Yes:
                    os.startfile(file_path)
            else:
                QMessageBox.critical(self, "Error", message)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar reporte: {str(e)}")

    # ------------------------------------------------------------------ #
    # Menú contextual
    # ------------------------------------------------------------------ #
    def _open_context_menu(self, pos: QPoint):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        self.table.selectRow(row)

        menu = QMenu(self)
        act_edit = menu.addAction("Editar…")
        act_export = menu.addAction("Generar PDF…")
        act_delete = menu.addAction("Eliminar…")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == act_edit:
            self._edit()
        elif action == act_export:
            self._export()
        elif action == act_delete:
            self._delete()