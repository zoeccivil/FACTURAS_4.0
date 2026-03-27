"""
Generador de reportes PDF para pagos de impuestos.
Exporta reportes mensuales de pagos (pagados, pendientes y totales) sin datos de ITBIS adelantados.
"""

from datetime import datetime
from typing import Dict, List, Optional
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
    KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from tax_payments_manager import TaxPaymentManager


class TaxPaymentReportGenerator:
    """Generador de reportes PDF para pagos de impuestos."""

    def __init__(self, company_name: str = ""):
        self.company_name = company_name
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Configura estilos personalizados para el reporte."""
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#0F172A"),
                spaceAfter=6,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="CustomHeading",
                parent=self.styles["Heading2"],
                fontSize=14,
                textColor=colors.HexColor("#1E293B"),
                spaceAfter=8,
                spaceBefore=10,
                fontName="Helvetica-Bold",
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="CustomSubtitle",
                parent=self.styles["Normal"],
                fontSize=11,
                textColor=colors.HexColor("#4B5563"),
                spaceAfter=8,
                alignment=TA_CENTER,
            )
        )

    def _create_header(self, report_data: Dict) -> List:
        """Crea el encabezado del reporte."""
        elements = []
        
        # Título
        elements.append(
            Paragraph("REPORTE DE PAGOS DE IMPUESTOS", self.styles["CustomTitle"])
        )
        
        # Empresa y fecha
        company_text = self.company_name or "Empresa"
        elements.append(
            Paragraph(f"Empresa: <b>{company_text}</b>", self.styles["CustomSubtitle"])
        )
        
        generated_at = report_data.get("generated_at")
        if isinstance(generated_at, datetime):
            date_str = generated_at.strftime("%d de %B de %Y a las %H:%M")
        else:
            date_str = str(generated_at)
        
        elements.append(
            Paragraph(
                f"Reporte generado: <b>{date_str}</b>",
                self.styles["CustomSubtitle"],
            )
        )
        
        elements.append(Spacer(1, 0.3 * inch))
        return elements

    def _create_overall_summary_table(self, summary: Dict) -> List:
        """Crea tabla con resumen general."""
        elements = []
        
        elements.append(
            Paragraph("RESUMEN GENERAL", self.styles["CustomHeading"])
        )
        
        # Crear tabla de resumen
        summary_data = [
            ["Concepto", "Cantidad", "Monto (RD$)"],
            [
                "Total Cálculos",
                str(summary.get("total_count", 0)),
                TaxPaymentManager.format_currency(summary.get("total_amount", 0)),
            ],
            [
                "✓ Pagados",
                str(summary.get("paid_count", 0)),
                TaxPaymentManager.format_currency(summary.get("paid_amount", 0)),
            ],
            [
                "⧗ Pendientes",
                str(summary.get("pending_count", 0)),
                TaxPaymentManager.format_currency(summary.get("pending_amount", 0)),
            ],
            [
                "% Pagado",
                f"{summary.get('paid_percentage', 0)}%",
                ""
            ],
        ]
        
        table = Table(summary_data, colWidths=[2.5 * inch, 1.5 * inch, 2 * inch])
        table.setStyle(
            TableStyle(
                [
                    # Encabezado
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    # Datos
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    # Fila de totales en negrita
                    ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F0F4F8")),
                ]
            )
        )
        
        elements.append(table)
        elements.append(Spacer(1, 0.2 * inch))
        
        return elements

    def _create_monthly_table(self, month_key: str, month_data: Dict) -> List:
        """Crea tabla para un mes específico."""
        elements = []
        
        summary = month_data.get("summary", {})
        calculations = month_data.get("calculations", [])
        
        # Encabezado del mes
        month_display = self._format_month(month_key)
        elements.append(
            Paragraph(f"MES: {month_display}", self.styles["CustomHeading"])
        )
        
        # Resumen del mes
        summary_text = (
            f"Total: <b>{TaxPaymentManager.format_currency(summary.get('total_amount', 0))}</b> | "
            f"Pagados: <b>{TaxPaymentManager.format_currency(summary.get('paid_amount', 0))}</b> | "
            f"Pendientes: <b>{TaxPaymentManager.format_currency(summary.get('pending_amount', 0))}</b>"
        )
        elements.append(
            Paragraph(summary_text, self.styles["Normal"])
        )
        elements.append(Spacer(1, 0.15 * inch))
        
        # Tabla de cálculos del mes
        if calculations:
            calc_table_data = [
                ["Nombre del Cálculo", "Fecha", "Monto (RD$)", "Estado"],
            ]
            
            for calc in calculations:
                calc_table_data.append([
                    calc.get("name", "N/A"),
                    self._format_date(calc.get("created_at", "")),
                    TaxPaymentManager.format_currency(calc.get("amount", 0)),
                    calc.get("status", "N/A"),
                ])
            
            table = Table(calc_table_data, colWidths=[2.5 * inch, 1.2 * inch, 1.3 * inch, 1.5 * inch])
            table.setStyle(
                TableStyle(
                    [
                        # Encabezado
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                        # Datos
                        ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                        ("ALIGN", (3, 1), (3, -1), "CENTER"),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            
            elements.append(table)
        else:
            elements.append(Paragraph("No hay cálculos en este mes.", self.styles["Normal"]))
        
        elements.append(Spacer(1, 0.25 * inch))
        return elements

    def _format_month(self, month_key: str) -> str:
        """Formatea clave de mes 'YYYY-MM' a texto legible."""
        if month_key == "Sin Fecha":
            return "Sin Fecha"
        try:
            date_obj = datetime.strptime(month_key, "%Y-%m")
            return date_obj.strftime("%B de %Y").capitalize()
        except Exception:
            return month_key

    def _format_date(self, date_value) -> str:
        """Formatea valor de fecha."""
        if isinstance(date_value, datetime):
            return date_value.strftime("%d/%m/%Y")
        try:
            date_str = str(date_value)[:10]
            if date_str:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                return date_obj.strftime("%d/%m/%Y")
        except Exception:
            pass
        return str(date_value)[:10] if date_value else "N/A"

    def generate_pdf(
        self,
        report_data: Dict,
        output_path: str,
        page_size=letter,
    ):
        """
        Genera reporte PDF completo.
        
        Args:
            report_data: Datos del reporte (resultado de TaxPaymentManager.generate_monthly_report_data)
            output_path: Ruta donde guardar el PDF
            page_size: Tamaño de página (letter o A4)
        
        Returns:
            Tupla (success: bool, message: str)
        """
        try:
            doc = SimpleDocTemplate(
                output_path,
                pagesize=page_size,
                rightMargin=0.5 * inch,
                leftMargin=0.5 * inch,
                topMargin=0.5 * inch,
                bottomMargin=0.5 * inch,
            )
            
            elements = []
            
            # Encabezado
            elements.extend(self._create_header(report_data))
            
            # Resumen general
            overall_summary = report_data.get("overall_summary", {})
            elements.extend(self._create_overall_summary_table(overall_summary))
            
            # Reportes mensuales
            monthly_data = report_data.get("monthly_data", {})
            month_count = 0
            
            for month_key in sorted(monthly_data.keys(), reverse=True):
                month_data = monthly_data[month_key]
                
                # Agregar salto de página cada 3 meses
                if month_count > 0 and month_count % 3 == 0:
                    elements.append(PageBreak())
                
                elements.extend(self._create_monthly_table(month_key, month_data))
                month_count += 1
            
            # Pie de página
            elements.append(Spacer(1, 0.3 * inch))
            footer_text = f"Fin del reporte - Generado automáticamente el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}"
            elements.append(
                Paragraph(footer_text, ParagraphStyle(
                    name="Footer",
                    parent=self.styles["Normal"],
                    fontSize=8,
                    textColor=colors.HexColor("#A0AEC0"),
                    alignment=TA_CENTER,
                ))
            )
            
            # Generar PDF
            doc.build(elements)
            
            return True, f"PDF generado exitosamente: {output_path}"
        
        except Exception as e:
            return False, f"Error al generar PDF: {str(e)}"

    @staticmethod
    def generate_payment_collection_summary(
        calculations: List[Dict],
        company_name: str = "",
        output_path: Optional[str] = None,
    ):
        """
        Genera un resumen simplificado de cobros pendientes.
        
        Args:
            calculations: Lista de cálculos
            company_name: Nombre de la empresa
            output_path: Si se proporciona, guarda en PDF
            
        Returns:
            Tupla (success: bool, message: str, report_data: Dict)
        """
        try:
            report_data = TaxPaymentManager.generate_monthly_report_data(
                calculations, company_name, include_details=True
            )
            
            if output_path:
                generator = TaxPaymentReportGenerator(company_name)
                success, msg = generator.generate_pdf(report_data, output_path)
                return success, msg, report_data
            
            return True, "Resumen generado exitosamente", report_data
        
        except Exception as e:
            return False, f"Error al generar resumen: {str(e)}", {}
