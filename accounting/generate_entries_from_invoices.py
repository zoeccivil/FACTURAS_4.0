# accounting/generate_entries_from_invoices.py
"""
Diálogo para generar asientos contables automáticamente desde facturas. 
Incluye barra de progreso y log en tiempo real.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTextEdit, QProgressBar, QDateEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt6.QtGui import QFont, QColor
import datetime


class InvoiceProcessingThread(QThread):
    """Thread para procesar facturas en segundo plano."""
    
    progress_update = pyqtSignal(int, str)  # (porcentaje, mensaje)
    finished_signal = pyqtSignal(bool, str, dict)  # (success, message, stats)
    
    def __init__(self, controller, company_id, start_date, end_date):
        super().__init__()
        self.controller = controller
        self.company_id = company_id
        self. start_date = start_date
        self.end_date = end_date
        self.stats = {
            "total_invoices": 0,
            "processed":  0,
            "errors": 0,
            "entries_created": 0
        }
    
    def run(self):
        """Procesa las facturas y genera asientos."""
        try:
            self. progress_update.emit(0, "🔍 Obteniendo facturas del periodo...")
            
            # Obtener facturas
            invoices = self._get_invoices()
            self.stats["total_invoices"] = len(invoices)
            
            if not invoices: 
                self.finished_signal.emit(True, "No hay facturas en el periodo seleccionado.", self.stats)
                return
            
            self.progress_update.emit(10, f"✅ {len(invoices)} facturas encontradas")
            
            # Procesar cada factura
            for idx, invoice in enumerate(invoices):
                try:
                    progress = int(10 + (80 * (idx + 1) / len(invoices)))
                    inv_num = invoice. get("invoice_number", "S/N")
                    inv_type = invoice.get("invoice_type", "")
                    
                    type_icon = "📥" if inv_type == "emitida" else "📤"
                    
                    self. progress_update.emit(
                        progress,
                        f"{type_icon} Procesando factura {idx + 1}/{len(invoices)}: {inv_num}"
                    )
                    
                    # Generar asiento
                    success = self._create_entry_from_invoice(invoice)
                    
                    if success: 
                        self.stats["processed"] += 1
                        self. stats["entries_created"] += 1
                        self.progress_update.emit(progress, f"  ✅ Asiento creado para {inv_num}")
                    else:
                        self.stats["errors"] += 1
                        self.progress_update.emit(progress, f"  ⚠️ Error en {inv_num}")
                    
                except Exception as e: 
                    self.stats["errors"] += 1
                    self. progress_update.emit(
                        progress,
                        f"  ❌ Error procesando {inv_num}: {str(e)[:50]}"
                    )
            
            self.progress_update. emit(100, "✅ Proceso completado")
            
            msg = (
                f"Proceso finalizado:\n\n"
                f"📊 Facturas procesadas: {self.stats['processed']}/{self.stats['total_invoices']}\n"
                f"✅ Asientos creados: {self.stats['entries_created']}\n"
                f"⚠️ Errores: {self. stats['errors']}"
            )
            
            self.finished_signal.emit(True, msg, self.stats)
            
        except Exception as e: 
            self.progress_update.emit(0, f"❌ Error fatal: {e}")
            self.finished_signal.emit(False, f"Error:  {e}", self.stats)
    
    def _get_invoices(self):
        """Obtiene facturas del periodo."""
        try:
            # Convertir fechas a strings
            start_str = self.start_date.strftime("%Y-%m-%d")
            end_str = self.end_date.strftime("%Y-%m-%d")
            
            # Obtener facturas de ingresos
            income = []
            try:
                if hasattr(self.controller, "get_emitted_invoices_for_period"):
                    income = self.controller.get_emitted_invoices_for_period(
                        self.company_id, start_str, end_str
                    ) or []
            except Exception as e:
                print(f"[INVOICE_THREAD] Error obteniendo ingresos: {e}")
            
            # Obtener facturas de gastos
            expenses = []
            try:
                if hasattr(self.controller, "_query_invoices"):
                    all_expenses = self.controller._query_invoices(
                        self.company_id,
                        None,  # mes
                        self.start_date.year,
                        "gasto"
                    ) or []
                    
                    # Filtrar gastos por rango de fechas
                    for exp in all_expenses:
                        exp_date = self._normalize_date(exp.get("invoice_date"))
                        if exp_date and self. start_date <= exp_date <= self.end_date:
                            expenses.append(exp)
            except Exception as e:
                print(f"[INVOICE_THREAD] Error obteniendo gastos: {e}")
            
            return income + expenses
            
        except Exception as e: 
            print(f"[INVOICE_THREAD] Error obteniendo facturas: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _normalize_date(self, value):
        """Normaliza fecha desde Firestore."""
        if value is None:
            return None
        if isinstance(value, datetime.date):
            return value
        if isinstance(value, datetime.datetime):
            return value. date()
        if hasattr(value, "date") and callable(value.date):
            return value. date()
        try:
            return datetime.datetime. strptime(str(value)[:10], "%Y-%m-%d").date()
        except:
            return None
    
    def _create_entry_from_invoice(self, invoice):
        """Crea asiento contable desde una factura."""
        try:
            inv_type = invoice.get("invoice_type")
            inv_date = self._normalize_date(invoice.get("invoice_date"))
            inv_num = invoice.get("invoice_number")
            third_party = invoice.get("third_party_name", "Cliente/Proveedor")
            
            # Montos
            total_rd = float(invoice.get("total_amount_rd", 0) or 0)
            if total_rd == 0:
                total = float(invoice.get("total_amount", 0) or 0)
                rate = float(invoice.get("exchange_rate", 1.0) or 1.0)
                total_rd = total * rate
            
            itbis = float(invoice.get("itbis", 0) or 0)
            rate = float(invoice.get("exchange_rate", 1.0) or 1.0)
            
            # Calcular montos en RD$
            itbis_rd = itbis * rate
            base = total_rd - itbis_rd
            
            lines = []
            
            if inv_type == "emitida":
                # ✅ FACTURA EMITIDA (INGRESO)
                # Débito:  Cuentas por Cobrar / Efectivo
                lines.append({
                    "account_id": "1.1.2.001",
                    "account_name": "Clientes Nacionales",
                    "debit":  total_rd,
                    "credit": 0.0,
                    "description":  f"Venta a {third_party}"
                })
                
                # Crédito: ITBIS por Pagar
                if itbis_rd > 0:
                    lines.append({
                        "account_id":  "2.1.2.001",
                        "account_name": "ITBIS por Pagar",
                        "debit": 0.0,
                        "credit": itbis_rd,
                        "description": f"ITBIS Factura {inv_num}"
                    })
                
                # Crédito: Ingreso
                lines.append({
                    "account_id": "4.1.1.001",
                    "account_name": "Ventas de Servicios",
                    "debit": 0.0,
                    "credit":  base,
                    "description": f"Venta según {inv_num}"
                })
                
            elif inv_type == "gasto":
                # ✅ FACTURA DE GASTO (COMPRA)
                # Débito: Gasto
                lines.append({
                    "account_id": "5.2.1.001",
                    "account_name": "Gastos Operacionales",
                    "debit": base,
                    "credit": 0.0,
                    "description": f"Compra a {third_party}"
                })
                
                # Débito: ITBIS por Compensar
                if itbis_rd > 0:
                    lines.append({
                        "account_id": "1.1.4.001",
                        "account_name": "ITBIS por Compensar",
                        "debit": itbis_rd,
                        "credit": 0.0,
                        "description": f"ITBIS {inv_num}"
                    })
                
                # Crédito: Cuentas por Pagar / Efectivo
                lines.append({
                    "account_id": "2.1.1.001",
                    "account_name": "Proveedores Locales",
                    "debit": 0.0,
                    "credit": total_rd,
                    "description": f"Compra según {inv_num}"
                })
            
            else:
                print(f"[INVOICE_THREAD] Tipo desconocido: {inv_type}")
                return False
            
            # Validar que el asiento esté balanceado
            total_debit = sum(line["debit"] for line in lines)
            total_credit = sum(line["credit"] for line in lines)
            
            if abs(total_debit - total_credit) >= 0.01:
                print(f"[INVOICE_THREAD] Asiento desbalanceado: D={total_debit}, C={total_credit}")
                return False
            
            # Crear asiento
            if not hasattr(self.controller, "create_journal_entry"):
                print(f"[INVOICE_THREAD] Controller no tiene create_journal_entry")
                return False
            
            success, msg = self.controller.create_journal_entry(
                company_id=self.company_id,
                entry_date=inv_date,
                reference=inv_num,
                description=f"Asiento automático desde factura {inv_num}",
                lines=lines
            )
            
            return success
            
        except Exception as e: 
            print(f"[INVOICE_THREAD] Error creando asiento: {e}")
            import traceback
            traceback. print_exc()
            return False


class GenerateEntriesFromInvoicesDialog(QDialog):
    """
    Diálogo para generar asientos desde facturas con progreso en tiempo real.
    """
    
    def __init__(self, parent, controller, company_id, company_name):
        super().__init__(parent)
        self.controller = controller
        self. company_id = company_id
        self.company_name = company_name
        self.processing_thread = None
        
        self.setWindowTitle("Generar Asientos desde Facturas")
        self.resize(750, 650)
        self.setModal(True)
        
        self._build_ui()
        self._apply_styles()
    
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)
        
        # === HEADER ===
        header_card = QFrame()
        header_card.setObjectName("headerCard")
        header_layout = QVBoxLayout(header_card)
        header_layout. setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(4)
        
        title = QLabel("🔄 Generación Automática de Asientos Contables")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A;")
        
        subtitle = QLabel(f"{self.company_name}")
        subtitle.setStyleSheet("font-size: 12px; color: #64748B;")
        
        info = QLabel(
            "Este proceso creará automáticamente asientos contables desde las facturas\n"
            "de ingresos y gastos registradas en el periodo seleccionado."
        )
        info.setStyleSheet("font-size: 11px; color: #94A3AF; margin-top: 4px;")
        info.setWordWrap(True)
        
        header_layout. addWidget(title)
        header_layout.addWidget(subtitle)
        header_layout.addWidget(info)
        root.addWidget(header_card)
        
        # === SELECCIÓN DE PERIODO ===
        period_card = QFrame()
        period_card.setObjectName("periodCard")
        period_layout = QVBoxLayout(period_card)
        period_layout.setContentsMargins(20, 16, 20, 16)
        period_layout.setSpacing(12)
        
        period_label = QLabel("📅 Periodo a Procesar:")
        period_label. setStyleSheet("font-weight: 700; color: #1E293B; font-size: 14px;")
        period_layout.addWidget(period_label)
        
        dates_row = QHBoxLayout()
        dates_row.setSpacing(12)
        
        lbl_from = QLabel("Desde:")
        lbl_from.setStyleSheet("color: #475569; font-weight: 600;")
        dates_row.addWidget(lbl_from)
        
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.setDisplayFormat("dd/MM/yyyy")
        self.start_date.setObjectName("modernDate")
        dates_row.addWidget(self.start_date)
        
        dates_row.addSpacing(20)
        
        lbl_to = QLabel("Hasta:")
        lbl_to.setStyleSheet("color: #475569; font-weight: 600;")
        dates_row.addWidget(lbl_to)
        
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setDisplayFormat("dd/MM/yyyy")
        self.end_date. setObjectName("modernDate")
        dates_row.addWidget(self.end_date)
        
        dates_row.addStretch()
        period_layout. addLayout(dates_row)
        
        root.addWidget(period_card)
        
        # === LOG DE PROGRESO ===
        log_label = QLabel("📝 Log de Proceso:")
        log_label.setStyleSheet("font-weight: 700; color: #1E293B; font-size: 14px;")
        root.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setObjectName("logText")
        self.log_text.setMinimumHeight(250)
        root.addWidget(self.log_text)
        
        # === BARRA DE PROGRESO ===
        progress_container = QVBoxLayout()
        progress_container.setSpacing(4)
        
        self.progress_label = QLabel("Esperando inicio...")
        self.progress_label.setStyleSheet("font-size: 12px; color: #64748B; font-weight: 600;")
        progress_container.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("modernProgress")
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        progress_container.addWidget(self. progress_bar)
        
        root.addLayout(progress_container)
        
        # === BOTONES ===
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self. btn_close = QPushButton("Cerrar")
        self.btn_close.setObjectName("secondaryButton")
        self.btn_close.clicked.connect(self.reject)
        self.btn_close.setEnabled(False)
        
        self.btn_start = QPushButton("▶️ Iniciar Proceso")
        self.btn_start.setObjectName("primaryButton")
        self.btn_start. clicked.connect(self._start_processing)
        
        btn_row.addWidget(self.btn_close)
        btn_row.addWidget(self.btn_start)
        
        root.addLayout(btn_row)
    
    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }
            
            QFrame#headerCard, QFrame#periodCard {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }
            
            QDateEdit#modernDate {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px 12px;
                color: #0F172A;
                font-size: 13px;
                font-weight: 500;
                min-width: 140px;
            }
            
            QDateEdit#modernDate: focus {
                border-color: #3B82F6;
                border-width: 2px;
            }
            
            QDateEdit#modernDate::drop-down {
                border:  none;
                width: 30px;
            }
            
            QTextEdit#logText {
                background-color: #0F172A;
                color: #10B981;
                font-family: 'Courier New', 'Consolas', monospace;
                font-size: 12px;
                border-radius: 8px;
                padding: 12px;
                border: 1px solid #1E293B;
            }
            
            QProgressBar#modernProgress {
                border:  2px solid #E5E7EB;
                border-radius: 8px;
                text-align:  center;
                height: 32px;
                font-weight: 700;
                font-size: 13px;
                color: #FFFFFF;
            }
            
            QProgressBar#modernProgress::chunk {
                background:  qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10B981,
                    stop:1 #059669
                );
                border-radius: 6px;
            }
            
            QPushButton#primaryButton {
                background-color:  #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 12px 28px;
                font-weight:  600;
                font-size: 14px;
                min-width:  180px;
            }
            
            QPushButton#primaryButton: hover {
                background-color:  #059669;
            }
            
            QPushButton#primaryButton:disabled {
                background-color: #9CA3AF;
            }
            
            QPushButton#secondaryButton {
                background-color: #F9FAFB;
                color: #374151;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                padding: 12px 28px;
                font-weight: 600;
                font-size: 14px;
                min-width: 120px;
            }
            
            QPushButton#secondaryButton:hover {
                background-color: #E5E7EB;
            }
        """)
    
    def _start_processing(self):
        """Inicia el procesamiento en un thread separado."""
        # Validar fechas
        start_py = self.start_date.date().toPyDate()
        end_py = self.end_date.date().toPyDate()
        
        if start_py > end_py:
            QMessageBox.warning(
                self,
                "Fechas Inválidas",
                "La fecha de inicio debe ser anterior a la fecha fin."
            )
            return
        
        # Deshabilitar controles
        self.btn_start.setEnabled(False)
        self.start_date.setEnabled(False)
        self.end_date. setEnabled(False)
        self.progress_label.setText("Procesando...")
        
        # Limpiar log
        self.log_text.clear()
        self.progress_bar.setValue(0)
        
        # Agregar mensaje inicial
        self.log_text. append(f"{'='*60}")
        self.log_text.append(f"  GENERACIÓN AUTOMÁTICA DE ASIENTOS CONTABLES")
        self.log_text.append(f"  Empresa: {self.company_name}")
        self.log_text. append(f"  Periodo:  {start_py.strftime('%d/%m/%Y')} - {end_py.strftime('%d/%m/%Y')}")
        self.log_text.append(f"{'='*60}")
        self.log_text.append("")
        
        # Crear y iniciar thread
        self.processing_thread = InvoiceProcessingThread(
            self.controller,
            self.company_id,
            start_py,
            end_py
        )
        
        self.processing_thread.progress_update.connect(self._on_progress_update)
        self.processing_thread.finished_signal.connect(self._on_finished)
        
        self.processing_thread.start()
    
    def _on_progress_update(self, percentage, message):
        """Actualiza el progreso y el log."""
        self.progress_bar. setValue(percentage)
        self.progress_label.setText(f"Progreso: {percentage}%")
        
        # Agregar al log con timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
        # Auto-scroll al final
        scrollbar = self.log_text. verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _on_finished(self, success, message, stats):
        """Maneja la finalización del proceso."""
        self.btn_close.setEnabled(True)
        self.btn_start.setText("✓ Proceso Completado")
        
        # Agregar resumen al log
        self.log_text.append("")
        self.log_text. append(f"{'='*60}")
        self.log_text.append(f"  RESUMEN FINAL")
        self.log_text.append(f"{'='*60}")
        self.log_text.append(f"  Total Facturas:     {stats['total_invoices']}")
        self.log_text.append(f"  ✅ Procesadas:      {stats['processed']}")
        self.log_text.append(f"  📝 Asientos Creados: {stats['entries_created']}")
        self.log_text.append(f"  ⚠️  Errores:         {stats['errors']}")
        self.log_text.append(f"{'='*60}")
        
        # Auto-scroll
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        if success:
            self.progress_label.setText("✅ Proceso completado exitosamente")
            QMessageBox.information(self, "✅ Proceso Completado", message)
        else:
            self.progress_label.setText("❌ Proceso completado con errores")
            QMessageBox.critical(self, "❌ Error", message)
    
    def closeEvent(self, event):
        """Maneja el cierre de la ventana."""
        if self.processing_thread and self. processing_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Proceso en Ejecución",
                "El proceso aún está en ejecución. ¿Desea cerrarlo de todas formas?",
                QMessageBox.StandardButton.Yes | QMessageBox. StandardButton.No
            )
            
            if reply == QMessageBox. StandardButton.Yes:
                self.processing_thread.terminate()
                self.processing_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()