# reporte_mensual_window.py

import os
import sys
import datetime
import tempfile
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
    QGroupBox,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor

# Tu módulo de generación de reportes
import report_generator


class ReportWindowQt(QDialog):
    """
    Ventana de Reporte Mensual, adaptada al estilo moderno (ModernMainWindow):

    - Header tipo card con título + filtros Mes/Año + botones de acción.
    - Resumen en un groupbox moderno.
    - Dos tablas lado a lado con estilo similar a la tabla del dashboard.
    - Maximizable y redimensionable.
    """
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.report_data = None

        company_name = (
            self.parent.company_selector.currentText()
            if hasattr(self.parent, "company_selector")
            else ""
        )

        self.setWindowTitle(f"Reporte Mensual - {company_name}")
        self.resize(1100, 720)

        # Habilitar botones de ventana y grip de tamaño
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.setSizeGripEnabled(True)

        self._build_ui()
        self._populate_years()
        self._generate_report()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Card principal
        card = QFrame()
        card.setObjectName("reportCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(12)

        # Header: título + subtítulo + filtros + botones
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        title_box = QVBoxLayout()
        title = QLabel("Reporte Mensual de Facturación")
        title.setStyleSheet("font-size: 17px; font-weight: 600; color: #0F172A;")
        self.subtitle_label = QLabel("")
        self.subtitle_label.setStyleSheet("font-size: 11px; color: #6B7280;")
        title_box.addWidget(title)
        title_box.addWidget(self.subtitle_label)
        header_row.addLayout(title_box)
        header_row.addStretch()

        # Filtros Mes / Año
        filters_row = QHBoxLayout()
        filters_row.setSpacing(6)

        lbl_mes = QLabel("Mes:")
        lbl_mes.setStyleSheet("color: #4B5563; font-size: 12px;")
        filters_row.addWidget(lbl_mes)

        self.month_cb = QComboBox()
        self.month_cb.setFixedWidth(90)
        # Mostrar 1..12 pero podrías usar nombres si prefieres
        self.month_cb.addItems([str(i) for i in range(1, 13)])
        self.month_cb.setCurrentIndex(QDate.currentDate().month() - 1)
        filters_row.addWidget(self.month_cb)

        lbl_anio = QLabel("Año:")
        lbl_anio.setStyleSheet("color: #4B5563; font-size: 12px;")
        filters_row.addWidget(lbl_anio)

        self.year_cb = QComboBox()
        self.year_cb.setEditable(False)
        self.year_cb.setFixedWidth(90)
        filters_row.addWidget(self.year_cb)

        header_row.addLayout(filters_row)

        # Botones de acción
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(6)

        btn_generate = QPushButton("Generar")
        btn_generate.setObjectName("primaryButton")
        btn_generate.clicked.connect(self._generate_report)

        btn_pdf = QPushButton("PDF")
        btn_pdf.setObjectName("secondaryButton")
        btn_pdf.clicked.connect(self._export_pdf)

        btn_xlsx = QPushButton("Excel")
        btn_xlsx.setObjectName("secondaryButton")
        btn_xlsx.clicked.connect(self._export_excel)

        buttons_row.addWidget(btn_generate)
        buttons_row.addWidget(btn_pdf)
        buttons_row.addWidget(btn_xlsx)

        header_row.addLayout(buttons_row)
        card_layout.addLayout(header_row)

        # Línea separadora
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        card_layout.addWidget(line)

        # Summary area
        summary_group = QGroupBox("Resumen General del Mes (RD$)")
        summary_group.setObjectName("dialogGroupBox")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.setContentsMargins(10, 8, 10, 8)
        summary_layout.setSpacing(4)

        self.summary_labels = {}
        items = [
            ("Total Ingresos", "total_ingresos", "#15803D"),
            ("Total Gastos", "total_gastos", "#B91C1C"),
            ("Total Neto", "total_neto", "#1D4ED8"),
            ("ITBIS Ingresos", "itbis_ingresos", "#15803D"),
            ("ITBIS Gastos", "itbis_gastos", "#B91C1C"),
            ("ITBIS Neto", "itbis_neto", "#1D4ED8"),
        ]

        for label_text, key, color in items:
            row = QHBoxLayout()
            row.setSpacing(6)
            lbl = QLabel(f"{label_text}:")
            lbl.setStyleSheet("color: #4B5563; font-size: 12px;")
            val = QLabel("RD$ 0.00")
            val.setStyleSheet(
                f"font-weight: 600; font-size: 13px; color: {color};"
            )
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            summary_layout.addLayout(row)
            self.summary_labels[key] = val

        card_layout.addWidget(summary_group)

        # Tables area (dos tablas lado a lado)
        tables_row = QHBoxLayout()
        tables_row.setSpacing(12)

        # Emitted invoices table
        emitted_group = QGroupBox("Facturas Emitidas (Ingresos)")
        emitted_group.setObjectName("dialogGroupBox")
        emitted_layout = QVBoxLayout(emitted_group)
        emitted_layout.setContentsMargins(10, 8, 10, 8)

        self.emitted_table = QTableWidget(0, 6)
        self.emitted_table.setHorizontalHeaderLabels(
            ["Fecha", "No. Fact.", "Empresa", "Monto Original", "ITBIS RD$", "Total RD$"]
        )

        eh = self.emitted_table.horizontalHeader()
        eh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        eh.setStretchLastSection(True)
        eh.setSectionsMovable(True)
        eh.setMinimumSectionSize(70)

        self.emitted_table.setAlternatingRowColors(False)
        self.emitted_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.emitted_table.verticalHeader().setVisible(False)

        emitted_layout.addWidget(self.emitted_table)
        tables_row.addWidget(emitted_group, 1)

        # Expenses table
        expenses_group = QGroupBox("Facturas de Gastos")
        expenses_group.setObjectName("dialogGroupBox")
        expenses_layout = QVBoxLayout(expenses_group)
        expenses_layout.setContentsMargins(10, 8, 10, 8)

        self.expenses_table = QTableWidget(0, 6)
        self.expenses_table.setHorizontalHeaderLabels(
            ["Fecha", "No. Fact.", "Empresa", "Monto Original", "ITBIS RD$", "Total RD$"]
        )

        eh2 = self.expenses_table.horizontalHeader()
        eh2.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        eh2.setStretchLastSection(True)
        eh2.setSectionsMovable(True)
        eh2.setMinimumSectionSize(70)

        self.expenses_table.setAlternatingRowColors(False)
        self.expenses_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.expenses_table.verticalHeader().setVisible(False)

        expenses_layout.addWidget(self.expenses_table)
        tables_row.addWidget(expenses_group, 1)

        card_layout.addLayout(tables_row, 1)

        root.addWidget(card)

        # Estilos para integrarlo con el estilo moderno
        self.setStyleSheet(
            self.styleSheet()
            + """
        QFrame#reportCard {
            background-color: #FFFFFF;
            border-radius: 12px;
            border: 1px solid #E2E8F0;
        }
        QGroupBox#dialogGroupBox {
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            margin-top: 8px;
        }
        QGroupBox#dialogGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px 0 4px;
            color: #1F2937;
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
        }
        QComboBox {
            background-color: #F9FAFB;
            border: 1px solid #D1D5DB;
            border-radius: 6px;
            padding: 3px 6px;
            color: #111827;
        }
        QComboBox:focus {
            border-color: #3B82F6;
        }
        QTableWidget {
            background-color: #FFFFFF;
            gridline-color: #E5E7EB;
            border-radius: 6px;
        }
        QHeaderView::section {
            background-color: #F9FAFB;
            padding: 4px;
            border: 1px solid #E5E7EB;
            font-weight: 500;
            color: #4B5563;
        }
        QPushButton#primaryButton {
            background-color: #1E293B;
            color: #FFFFFF;
            padding: 6px 12px;
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
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px solid #D1D5DB;
            font-weight: 500;
        }
        QPushButton#secondaryButton:hover {
            background-color: #E5E7EB;
        }
        """
        )

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------
    def _populate_years(self):
        self.year_cb.clear()
        try:
            company_id = self.parent.get_current_company_id()
        except Exception:
            company_id = None

        years = []
        try:
            if company_id and hasattr(self.controller, "get_unique_invoice_years"):
                years = self.controller.get_unique_invoice_years(company_id) or []
            years = (
                sorted({int(y) for y in years if y not in (None, "")}, reverse=True)
                if years
                else []
            )
        except Exception:
            years = []

        if years:
            for y in years:
                self.year_cb.addItem(str(y))
            self.year_cb.setCurrentIndex(0)
        else:
            self.year_cb.addItem(str(datetime.date.today().year))
            self.year_cb.setCurrentIndex(0)

        # actualizar subtítulo inicial
        self._update_subtitle()

    def _update_subtitle(self):
        try:
            month = int(self.month_cb.currentText())
            year = int(self.year_cb.currentText())
        except Exception:
            month = QDate.currentDate().month()
            year = QDate.currentDate().year()

        company_name = (
            self.parent.company_selector.currentText()
            if hasattr(self.parent, "company_selector")
            else ""
        )
        period_str = f"{year}-{month:02d}"
        self.subtitle_label.setText(f"Empresa: {company_name} – Período: {period_str}")

    def _generate_report(self):
        try:
            month = int(self.month_cb.currentText())
            year = int(self.year_cb.currentText())
        except Exception:
            QMessageBox.critical(self, "Error", "Mes y año deben ser números válidos.")
            return

        # Obtener empresa activa desde el parent (ModernMainWindow)
        company_id = None
        try:
            if hasattr(self.parent, "get_current_company_id"):
                company_id = self.parent.get_current_company_id()
        except Exception:
            company_id = None

        if not company_id:
            QMessageBox.warning(
                self, "Sin Empresa", "Selecciona una empresa activa."
            )
            return

        self._update_subtitle()

        try:
            raw = (
                self.controller.get_monthly_report_data(company_id, month, year)
                or {}
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo obtener datos: {e}")
            return

        def _normalize_list(lst):
            normalized = []
            for r in lst or []:
                try:
                    normalized.append(dict(r))
                except Exception:
                    if isinstance(r, dict):
                        normalized.append(r)
                    else:
                        try:
                            normalized.append({k: r[k] for k in r.keys()})
                        except Exception:
                            normalized.append(r)
            return normalized

        self.report_data = {
            "summary": raw.get("summary", {}),
            "emitted_invoices": _normalize_list(raw.get("emitted_invoices", [])),
            "expense_invoices": _normalize_list(raw.get("expense_invoices", [])),
        }
        self._populate_report()

    def _populate_report(self):
        # clear tables
        for tbl in (self.emitted_table, self.expenses_table):
            tbl.setRowCount(0)

        # reset summary labels
        for key, lbl in self.summary_labels.items():
            lbl.setText("RD$ 0.00")

        if not self.report_data:
            QMessageBox.information(
                self,
                "Sin Datos",
                "No se encontraron transacciones para el período seleccionado.",
            )
            return

        # ✅ HELPER PARA FORMATEAR FECHAS (solo YYYY-MM-DD)
        def format_date(date_val) -> str:
            """Convierte cualquier formato de fecha a string YYYY-MM-DD"""
            if not date_val:
                return ""
            
            # Si ya es datetime. datetime o datetime. date
            if isinstance(date_val, datetime.datetime):
                return date_val.strftime("%Y-%m-%d")
            if isinstance(date_val, datetime. date):
                return date_val.strftime("%Y-%m-%d")
            
            # Si es string, extraer solo los primeros 10 caracteres
            date_str = str(date_val).strip()
            if len(date_str) >= 10:
                # Formato: "2026-01-08 00:00:00" -> "2026-01-08"
                return date_str[:10]
            
            return date_str

        summary = self.report_data.get("summary", {})
        self.summary_labels. get("total_ingresos").setText(
            f"RD$ {summary.get('total_ingresos', 0.0):,.2f}"
        )
        self.summary_labels.get("total_gastos").setText(
            f"RD$ {summary.get('total_gastos', 0.0):,.2f}"
        )
        self.summary_labels.get("total_neto").setText(
            f"RD$ {summary.get('total_neto', 0.0):,.2f}"
        )
        self.summary_labels.get("itbis_ingresos").setText(
            f"RD$ {summary.get('itbis_ingresos', 0.0):,.2f}"
        )
        self.summary_labels.get("itbis_gastos").setText(
            f"RD$ {summary.get('itbis_gastos', 0.0):,.2f}"
        )
        self.summary_labels.get("itbis_neto").setText(
            f"RD$ {summary.get('itbis_neto', 0.0):,.2f}"
        )

        # populate emitted (✅ FECHA CORREGIDA)
        for inv in self.report_data.get("emitted_invoices", []):
            row = self.emitted_table.rowCount()
            self.emitted_table.insertRow(row)

            monto_orig = f"{float(inv.get('total_amount', 0.0)):,.2f} {inv.get('currency', 'RD$')}"
            itbis_rd = float(inv.get("itbis", 0.0)) * float(
                inv.get("exchange_rate", 1.0) or 1.0
            )
            total_rd = float(inv.get("total_amount_rd", 0.0))

            # ✅ USAR format_date()
            self.emitted_table.setItem(
                row, 0, QTableWidgetItem(format_date(inv.get("invoice_date")))
            )
            self.emitted_table. setItem(
                row, 1, QTableWidgetItem(str(inv.get("invoice_number", "")))
            )
            self.emitted_table.setItem(
                row, 2, QTableWidgetItem(str(inv.get("third_party_name", "")))
            )

            item_mo = QTableWidgetItem(monto_orig)
            item_mo.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt. AlignmentFlag.AlignVCenter
            )
            self.emitted_table.setItem(row, 3, item_mo)

            item_it = QTableWidgetItem(f"{itbis_rd:,.2f}")
            item_it.setTextAlignment(
                Qt. AlignmentFlag.AlignRight | Qt.AlignmentFlag. AlignVCenter
            )
            self.emitted_table. setItem(row, 4, item_it)

            item_tr = QTableWidgetItem(f"{total_rd:,.2f}")
            item_tr.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.emitted_table.setItem(row, 5, item_tr)

        # populate expenses (✅ FECHA CORREGIDA)
        for inv in self.report_data.get("expense_invoices", []):
            row = self.expenses_table. rowCount()
            self.expenses_table.insertRow(row)

            monto_orig = f"{float(inv.get('total_amount', 0.0)):,.2f} {inv.get('currency', 'RD$')}"
            itbis_rd = float(inv.get("itbis", 0.0)) * float(
                inv. get("exchange_rate", 1.0) or 1.0
            )
            total_rd = float(inv.get("total_amount_rd", 0.0))

            # ✅ USAR format_date()
            self.expenses_table.setItem(
                row, 0, QTableWidgetItem(format_date(inv.get("invoice_date")))
            )
            self.expenses_table.setItem(
                row, 1, QTableWidgetItem(str(inv.get("invoice_number", "")))
            )
            self.expenses_table.setItem(
                row, 2, QTableWidgetItem(str(inv.get("third_party_name", "")))
            )

            item_mo = QTableWidgetItem(monto_orig)
            item_mo.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.expenses_table.setItem(row, 3, item_mo)

            item_it = QTableWidgetItem(f"{itbis_rd:,.2f}")
            item_it.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.expenses_table.setItem(row, 4, item_it)

            item_tr = QTableWidgetItem(f"{total_rd:,.2f}")
            item_tr.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.expenses_table.setItem(row, 5, item_tr)
    # ------------------------------------------------------------------
    # Exportar PDF / Excel
    # ------------------------------------------------------------------
    def _export_pdf(self):
        """Exporta el reporte mensual a PDF con adjuntos desde Firebase Storage."""
        if not self.report_data:
            QMessageBox.warning(
                self, "Sin Datos", "Primero debes generar un reporte."
            )
            return

        company_name = (
            self.parent.company_selector.currentText()
            if hasattr(self.parent, "company_selector")
            else "empresa"
        )

        fname, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Reporte PDF",
            f"Reporte_{company_name.replace(' ', '_')}_{self.month_cb.currentText()}_{self.year_cb.currentText()}.pdf",
            "PDF Files (*.pdf)",
        )
        if not fname:
            return

        # ========================================
        # CREAR VENTANA DE PROGRESO
        # ========================================
        from pdf_progress_dialog import PDFProgressDialog
        
        progress_dialog = PDFProgressDialog(self)
        progress_dialog.set_title("Generando Reporte PDF...")
        progress_dialog.set_step("Preparando datos...")
        progress_dialog.show()
        
        # Forzar actualización de UI
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        try:
            # ========================================
            # PASO 1: RECOPILAR FACTURAS
            # ========================================
            progress_dialog.set_step("📊 Recopilando facturas...")
            progress_dialog.set_progress(10)
            progress_dialog.append_log_info("Iniciando generación de PDF...")
            QApplication.processEvents()
            
            all_invoices = (
                (self.report_data.get("emitted_invoices") or [])
                + (self.report_data.get("expense_invoices") or [])
            )
            
            total_invoices = len(all_invoices)
            emitidas = len(self.report_data.get("emitted_invoices", []))
            gastos = len(self.report_data.get("expense_invoices", []))
            
            progress_dialog.append_log(f"Total de facturas: {total_invoices}")
            progress_dialog.append_log(f"  • Emitidas: {emitidas}")
            progress_dialog.append_log(f"  • Gastos: {gastos}")
            QApplication.processEvents()
            
            # ========================================
            # PASO 2: ANÁLISIS DE ADJUNTOS
            # ========================================
            progress_dialog.set_step("🔍 Analizando adjuntos...")
            progress_dialog.set_progress(20)
            QApplication.processEvents()
            
            with_storage = sum(1 for inv in all_invoices if inv.get("attachment_storage_path") or inv.get("storage_path"))
            without_storage = total_invoices - with_storage
            
            progress_dialog.update_stats(
                total=total_invoices,
                with_attachment=with_storage,
                without_attachment=without_storage,
                downloaded=0
            )
            
            progress_dialog.append_log_info(f"Facturas con adjunto en Storage: {with_storage}")
            progress_dialog.append_log_warning(f"Facturas sin adjunto: {without_storage}")
            
            # Listar facturas sin adjunto
            if without_storage > 0:
                progress_dialog.append_log("")
                progress_dialog.append_log_warning("Facturas SIN adjunto:")
                count = 0
                for inv in all_invoices:
                    if not (inv.get("attachment_storage_path") or inv.get("storage_path")):
                        inv_num = inv.get("invoice_number", "N/A")
                        progress_dialog.append_log(f"  • {inv_num}", "#64748B")
                        count += 1
                        if count >= 10:  # Limitar a 10 para no saturar el log
                            if without_storage > 10:
                                progress_dialog.append_log(f"  ... y {without_storage - 10} más", "#64748B")
                            break
            
            QApplication.processEvents()
            
            # ========================================
            # PASO 3: DESCARGAR ADJUNTOS
            # ========================================
            progress_dialog.set_step("📥 Descargando adjuntos desde Firebase Storage...")
            progress_dialog.set_progress(30)
            progress_dialog.append_log("")
            progress_dialog.append_log_info("Iniciando descarga de adjuntos...")
            QApplication.processEvents()
            
            local_attachments: dict[str, str] = {}
            
            if hasattr(self.controller, "download_invoice_attachments_for_report") and with_storage > 0:
                # Descargar con actualización de progreso
                import tempfile
                import os
                
                temp_dir = tempfile.mkdtemp(prefix="invoice_attachments_")
                progress_dialog.append_log(f"Carpeta temporal: {temp_dir}", "#64748B")
                
                downloaded_count = 0
                failed_count = 0
                
                for idx, inv in enumerate(all_invoices, 1):
                    inv_id = str(inv.get("id") or inv.get("invoice_number") or "")
                    storage_path = inv.get("attachment_storage_path") or inv.get("storage_path")
                    
                    if not storage_path:
                        continue
                    
                    # Actualizar progreso
                    progress_value = 30 + int((idx / with_storage) * 40)  # 30% a 70%
                    progress_dialog.set_progress(progress_value)
                    progress_dialog.set_detail(f"Descargando {idx}/{with_storage}: {inv_id}")
                    QApplication.processEvents()
                    
                    try:
                        ext = os.path.splitext(storage_path)[1] or ".jpg"
                        temp_file = os.path.join(temp_dir, f"{inv_id}{ext}")
                        
                        if hasattr(self.controller, "download_attachment_from_storage"):
                            success = self.controller.download_attachment_from_storage(
                                storage_path, 
                                temp_file
                            )
                            
                            if success and os.path.exists(temp_file):
                                local_attachments[inv_id] = temp_file
                                downloaded_count += 1
                                size_kb = os.path.getsize(temp_file) / 1024
                                progress_dialog.append_log_success(f"{inv_id} ({size_kb:.1f} KB)")
                                
                                # Actualizar estadísticas
                                progress_dialog.update_stats(
                                    total=total_invoices,
                                    with_attachment=with_storage,
                                    without_attachment=without_storage,
                                    downloaded=downloaded_count
                                )
                            else:
                                failed_count += 1
                                progress_dialog.append_log_error(f"{inv_id} - Descarga falló")
                        
                    except Exception as e:
                        failed_count += 1
                        progress_dialog.append_log_error(f"{inv_id} - Error: {str(e)}")
                
                progress_dialog.append_log("")
                progress_dialog.append_log_info(f"Descarga completada: {downloaded_count} exitosos, {failed_count} fallidos")
            
            # ========================================
            # PASO 4: RESOLVER RUTAS
            # ========================================
            progress_dialog.set_step("🔍 Resolviendo rutas de adjuntos...")
            progress_dialog.set_progress(75)
            progress_dialog.append_log("")
            progress_dialog.append_log_info("Resolviendo rutas de adjuntos...")
            QApplication.processEvents()
            
            resolved_count = 0
            
            for section in ("emitted_invoices", "expense_invoices"):
                for inv in self.report_data.get(section, []):
                    inv_id = str(inv.get("id") or inv.get("invoice_number") or "")
                    
                    if inv_id and inv_id in local_attachments:
                        resolved_path = local_attachments[inv_id]
                        if os.path.exists(resolved_path):
                            inv["attachment_resolved"] = resolved_path
                            resolved_count += 1
                        else:
                            inv["attachment_resolved"] = None
                    else:
                        inv["attachment_resolved"] = None
            
            progress_dialog.append_log_info(f"Adjuntos resueltos: {resolved_count}/{total_invoices}")
            QApplication.processEvents()
            
            # ========================================
            # PASO 5: GENERAR PDF
            # ========================================
            progress_dialog.set_step("📄 Generando PDF final...")
            progress_dialog.set_progress(85)
            progress_dialog.append_log("")
            progress_dialog.append_log_info("Construyendo documento PDF...")
            QApplication.processEvents()
            
            # Buscar función de generación
            func = getattr(report_generator, "generate_professional_pdf", None)
            if func is None:
                for alt in ("generate_professional_report", "generate_pdf_report", "generate_report_pdf"):
                    if hasattr(report_generator, alt):
                        func = getattr(report_generator, alt)
                        break
            
            if func is None:
                progress_dialog.finish(False)
                progress_dialog.append_log_error("Función de generación de PDF no encontrada")
                progress_dialog.exec()
                return
            
            # Generar PDF
            try:
                ok, msg = func(
                    self.report_data,
                    fname,
                    company_name,
                    self.month_cb.currentText(),
                    self.year_cb.currentText(),
                    None,
                )
            except TypeError:
                ok, msg = func(
                    self.report_data,
                    fname,
                    company_name,
                    self.month_cb.currentText(),
                    self.year_cb.currentText(),
                )
            
            # ========================================
            # RESULTADO FINAL
            # ========================================
            progress_dialog.set_progress(100)
            
            if ok:
                progress_dialog.finish(True)
                progress_dialog.append_log("")
                progress_dialog.append_log_success(f"PDF guardado en: {fname}")
                progress_dialog.append_log_info(f"Adjuntos incluidos: {resolved_count}/{total_invoices}")
                
                # Mostrar diálogo y luego mensaje
                progress_dialog.exec()
                
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Reporte generado exitosamente.\n\n"
                    f"Ruta: {fname}\n"
                    f"Adjuntos incluidos: {resolved_count}/{total_invoices}"
                )
            else:
                progress_dialog.finish(False)
                progress_dialog.append_log_error(msg)
                progress_dialog.exec()
                
                QMessageBox.critical(self, "Error", msg)
        
        except Exception as e:
            progress_dialog.finish(False)
            progress_dialog.append_log_error(f"Error crítico: {str(e)}")
            progress_dialog.exec()
            
            QMessageBox.critical(self, "Error", f"Error al generar PDF: {e}")
            import traceback
            traceback.print_exc()


    def _export_excel(self):
        if not self.report_data:
            QMessageBox.warning(
                self, "Sin Datos", "Primero debes generar un reporte."
            )
            return

        company_name = (
            self.parent.company_selector.currentText()
            if hasattr(self.parent, "company_selector")
            else "empresa"
        )

        fname, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Reporte Excel",
            f"Reporte_{company_name.replace(' ', '_')}_{self.month_cb.currentText()}_{self.year_cb.currentText()}.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not fname:
            return

        try:
            ok, msg = report_generator.generate_excel_report(
                self.report_data, fname
            )
            if ok:
                QMessageBox.information(self, "Éxito", msg)
            else:
                QMessageBox.critical(self, "Error", msg)
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"No se pudo generar el Excel: {e}"
            )