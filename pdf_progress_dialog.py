# pdf_progress_dialog.py

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QTextEdit,
    QPushButton,
    QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor


class PDFProgressDialog(QDialog):
    """
    Ventana de progreso para la generación de PDF con adjuntos.
    
    Muestra:
    - Título del proceso
    - Barra de progreso con porcentaje
    - Texto del paso actual
    - Log detallado con scroll
    - Estadísticas de adjuntos
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generando PDF...")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self._build_ui()
    
    def _build_ui(self):
        """Construye la interfaz."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # === TÍTULO ===
        self.title_label = QLabel("Generando PDF...")
        self.title_label.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #0F172A;"
        )
        layout.addWidget(self.title_label)
        
        # === PASO ACTUAL ===
        self.step_label = QLabel("Preparando reporte...")
        self.step_label.setStyleSheet(
            "font-size: 13px; color: #475569; margin-bottom: 8px;"
        )
        layout.addWidget(self.step_label)
        
        # === BARRA DE PROGRESO ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - %v/%m")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #E5E7EB;
                border-radius: 8px;
                text-align: center;
                background-color: #F9FAFB;
                color: #0F172A;
                font-weight: 600;
                font-size: 13px;
                height: 28px;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6,
                    stop:1 #2563EB
                );
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # === DETALLES DEL PROGRESO ===
        self.detail_label = QLabel("Procesando anexo 1/3")
        self.detail_label.setStyleSheet(
            "font-size: 12px; color: #64748B; margin-top: 4px;"
        )
        layout.addWidget(self.detail_label)
        
        # === SEPARADOR ===
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #E5E7EB; margin: 8px 0px;")
        layout.addWidget(separator)
        
        # === ESTADÍSTICAS ===
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB;
                border-radius: 8px;
                border: 1px solid #E5E7EB;
                padding: 12px;
            }
        """)
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setSpacing(6)
        
        stats_title = QLabel("📊 Estadísticas de Adjuntos")
        stats_title.setStyleSheet("font-weight: 700; color: #1E293B; font-size: 13px;")
        stats_layout.addWidget(stats_title)
        
        self.stats_total = QLabel("Total de facturas: 0")
        self.stats_total.setStyleSheet("color: #475569; font-size: 12px;")
        stats_layout.addWidget(self.stats_total)
        
        self.stats_with_attachment = QLabel("✅ Con adjunto en Storage: 0")
        self.stats_with_attachment.setStyleSheet("color: #15803D; font-size: 12px; font-weight: 600;")
        stats_layout.addWidget(self.stats_with_attachment)
        
        self.stats_without_attachment = QLabel("⚠️ Sin adjunto: 0")
        self.stats_without_attachment.setStyleSheet("color: #DC2626; font-size: 12px; font-weight: 600;")
        stats_layout.addWidget(self.stats_without_attachment)
        
        self.stats_downloaded = QLabel("📥 Descargados exitosamente: 0")
        self.stats_downloaded.setStyleSheet("color: #0F172A; font-size: 12px;")
        stats_layout.addWidget(self.stats_downloaded)
        
        layout.addWidget(stats_frame)
        
        # === LOG DETALLADO ===
        log_label = QLabel("📝 Log Detallado:")
        log_label.setStyleSheet("font-weight: 600; color: #1E293B; margin-top: 8px;")
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                color: #0F172A;
            }
        """)
        layout.addWidget(self.log_text, 1)  # Stretch = 1 para que ocupe espacio disponible
        
        # === BOTÓN CANCELAR (OPCIONAL) ===
        self.btn_cancel = QPushButton("❌ Cancelar")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #F9FAFB;
                color: #374151;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #E5E7EB;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setVisible(False)  # Oculto por defecto
        layout.addWidget(self.btn_cancel, alignment=Qt.AlignmentFlag.AlignRight)
        
        # Aplicar estilos globales
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }
        """)
    
    # ========================================
    # MÉTODOS PÚBLICOS PARA ACTUALIZAR UI
    # ========================================
    
    def set_title(self, title: str):
        """Actualiza el título principal."""
        self.title_label.setText(title)
    
    def set_step(self, step_text: str):
        """Actualiza el texto del paso actual."""
        self.step_label.setText(step_text)
    
    def set_detail(self, detail_text: str):
        """Actualiza el detalle del progreso."""
        self.detail_label.setText(detail_text)
    
    def set_progress(self, value: int, maximum: int = 100):
        """
        Actualiza la barra de progreso.
        
        Args:
            value: Valor actual
            maximum: Valor máximo (default 100)
        """
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)
    
    def update_stats(
        self,
        total: int = 0,
        with_attachment: int = 0,
        without_attachment: int = 0,
        downloaded: int = 0
    ):
        """
        Actualiza las estadísticas de adjuntos.
        
        Args:
            total: Total de facturas
            with_attachment: Facturas con adjunto en Storage
            without_attachment: Facturas sin adjunto
            downloaded: Adjuntos descargados exitosamente
        """
        self.stats_total.setText(f"Total de facturas: {total}")
        self.stats_with_attachment.setText(f"✅ Con adjunto en Storage: {with_attachment}")
        self.stats_without_attachment.setText(f"⚠️ Sin adjunto: {without_attachment}")
        self.stats_downloaded.setText(f"📥 Descargados exitosamente: {downloaded}")
    
    def append_log(self, message: str, color: str = "#0F172A"):
        """
        Agrega una línea al log.
        
        Args:
            message: Mensaje a agregar
            color: Color del texto (hex)
        """
        self.log_text.append(f'<span style="color: {color};">{message}</span>')
        
        # Auto-scroll al final
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def append_log_success(self, message: str):
        """Agrega un mensaje de éxito al log."""
        self.append_log(f"✅ {message}", "#15803D")
    
    def append_log_error(self, message: str):
        """Agrega un mensaje de error al log."""
        self.append_log(f"❌ {message}", "#DC2626")
    
    def append_log_warning(self, message: str):
        """Agrega un mensaje de advertencia al log."""
        self.append_log(f"⚠️ {message}", "#EA580C")
    
    def append_log_info(self, message: str):
        """Agrega un mensaje informativo al log."""
        self.append_log(f"ℹ️ {message}", "#475569")
    
    def finish(self, success: bool = True):
        """
        Finaliza el proceso.
        
        Args:
            success: Si el proceso fue exitoso
        """
        if success:
            self.set_title("✅ PDF Generado Exitosamente")
            self.set_step("Proceso completado")
            self.progress_bar.setValue(self.progress_bar.maximum())
            self.append_log_success("PDF generado exitosamente")
        else:
            self.set_title("❌ Error al Generar PDF")
            self.set_step("Proceso interrumpido")
            self.append_log_error("Error durante la generación del PDF")
        
        # Cambiar botón a "Cerrar"
        self.btn_cancel.setText("✅ Cerrar")
        self.btn_cancel.setVisible(True)
        self.btn_cancel.clicked.disconnect()
        self.btn_cancel.clicked.connect(self.accept)