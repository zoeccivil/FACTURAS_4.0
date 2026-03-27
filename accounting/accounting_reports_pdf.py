"""
accounting_reports_pdf.py
Generador de reportes contables en PDF profesionales
"""

from typing import Optional
import datetime
from io import BytesIO

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, PageBreak, Image
    )
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class AccountingReportsPDF:
    """
    Generador de reportes contables en PDF con formato profesional.
    
    Reportes disponibles:
    - Balance General
    - Estado de Resultados
    - Libro Mayor
    - Comprobante de Asiento
    """
    
    def __init__(self, company_name: str):
        """
        Args:
            company_name: Nombre de la empresa para los reportes
        """
        self.company_name = company_name
        
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "ReportLab no está instalado. "
                "Instala con: pip install reportlab"
            )
    
    def generate_balance_sheet_pdf(
        self,
        filename: str,
        balance_data: dict,
        period: str
    ) -> bool:
        """
        Genera PDF del Balance General.
        
        Args:
            filename: Ruta donde guardar el PDF
            balance_data: Datos del balance con estructura:
                {
                    'activos': {
                        'corrientes': [...],
                        'no_corrientes': [...],
                        'total': float
                    },
                    'pasivos': {...},
                    'patrimonio': {...}
                }
            period: Periodo del reporte (ej: "Diciembre 2025")
        
        Returns:
            True si se generó exitosamente
        """
        try:
            doc = SimpleDocTemplate(filename, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Título
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1E40AF'),
                alignment=TA_CENTER,
                spaceAfter=12
            )
            
            story.append(Paragraph(self.company_name, title_style))
            story.append(Paragraph("BALANCE GENERAL", title_style))
            story.append(Paragraph(f"Al {period}", styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
            
            # Tabla de activos
            self._add_balance_section(story, "ACTIVOS", balance_data.get('activos', {}))
            story.append(Spacer(1, 0.2*inch))
            
            # Tabla de pasivos
            self._add_balance_section(story, "PASIVOS", balance_data.get('pasivos', {}))
            story.append(Spacer(1, 0.2*inch))
            
            # Tabla de patrimonio
            self._add_balance_section(story, "PATRIMONIO", balance_data.get('patrimonio', {}))
            story.append(Spacer(1, 0.3*inch))
            
            # Verificación
            total_activos = balance_data.get('activos', {}).get('total', 0)
            total_pasivos = balance_data.get('pasivos', {}).get('total', 0)
            total_patrimonio = balance_data.get('patrimonio', {}).get('total', 0)
            
            # Calculate difference with sign to show direction of imbalance
            difference = total_activos - (total_pasivos + total_patrimonio)
            verification_label = "Cuadrado ✓" if abs(difference) < 0.01 else "Diferencia"
            
            verification_data = [
                ['Total Activos:', f'RD$ {total_activos:,.2f}'],
                ['Total Pasivos:', f'RD$ {total_pasivos:,.2f}'],
                ['Total Patrimonio:', f'RD$ {total_patrimonio:,.2f}'],
                ['', ''],
                [f'{verification_label}:', f'RD$ {difference:,.2f}']
            ]
            
            verification_table = Table(verification_data, colWidths=[4*inch, 2*inch])
            verification_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LINEABOVE', (0, 4), (-1, 4), 2, colors.black),
            ]))
            
            story.append(verification_table)
            
            # Generar PDF
            doc.build(story)
            return True
            
        except Exception as e:
            print(f"[PDF_GENERATOR] Error generando Balance General: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _add_balance_section(self, story, section_title: str, section_data: dict):
        """Agrega una sección del balance (Activos, Pasivos o Patrimonio)"""
        styles = getSampleStyleSheet()
        
        # Título de sección
        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=8
        )
        
        story.append(Paragraph(section_title, section_style))
        
        # Datos de la tabla
        table_data = [['Cuenta', 'Código', 'Saldo']]
        
        # Corrientes
        if 'corrientes' in section_data:
            table_data.append(['Corrientes', '', ''])
            for item in section_data['corrientes']:
                table_data.append([
                    f"  {item.get('name', '')}",
                    item.get('code', ''),
                    f"RD$ {item.get('balance', 0):,.2f}"
                ])
        
        # No corrientes
        if 'no_corrientes' in section_data:
            table_data.append(['No Corrientes', '', ''])
            for item in section_data['no_corrientes']:
                table_data.append([
                    f"  {item.get('name', '')}",
                    item.get('code', ''),
                    f"RD$ {item.get('balance', 0):,.2f}"
                ])
        
        # Total
        total = section_data.get('total', 0)
        table_data.append(['', 'TOTAL', f"RD$ {total:,.2f}"])
        
        # Crear tabla
        table = Table(table_data, colWidths=[3*inch, 1.5*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
        ]))
        
        story.append(table)
    
    def generate_income_statement_pdf(
        self,
        filename: str,
        income_data: dict,
        period: str
    ) -> bool:
        """
        Genera PDF del Estado de Resultados.
        
        Args:
            filename: Ruta donde guardar el PDF
            income_data: Datos con estructura:
                {
                    'ingresos_operacionales': float,
                    'costo_ventas': float,
                    'utilidad_bruta': float,
                    'gastos_operacionales': float,
                    'gastos_financieros': float,
                    'utilidad_neta': float
                }
            period: Periodo del reporte
        
        Returns:
            True si se generó exitosamente
        """
        try:
            doc = SimpleDocTemplate(filename, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Título
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1E40AF'),
                alignment=TA_CENTER,
                spaceAfter=12
            )
            
            story.append(Paragraph(self.company_name, title_style))
            story.append(Paragraph("ESTADO DE RESULTADOS", title_style))
            story.append(Paragraph(f"Periodo: {period}", styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
            
            # Datos de la tabla
            table_data = [
                ['Concepto', 'Monto'],
                ['', ''],
                ['Ingresos Operacionales', f"RD$ {income_data.get('ingresos_operacionales', 0):,.2f}"],
                ['(-) Costo de Ventas', f"RD$ {income_data.get('costo_ventas', 0):,.2f}"],
                ['', ''],
                ['= Utilidad Bruta', f"RD$ {income_data.get('utilidad_bruta', 0):,.2f}"],
                ['', ''],
                ['(-) Gastos Operacionales', f"RD$ {income_data.get('gastos_operacionales', 0):,.2f}"],
                ['', ''],
                ['= Utilidad Operacional', f"RD$ {income_data.get('utilidad_operacional', 0):,.2f}"],
                ['', ''],
                ['(-) Gastos Financieros', f"RD$ {income_data.get('gastos_financieros', 0):,.2f}"],
                ['(+) Otros Ingresos', f"RD$ {income_data.get('otros_ingresos', 0):,.2f}"],
                ['(-) Otros Gastos', f"RD$ {income_data.get('otros_gastos', 0):,.2f}"],
                ['', ''],
                ['= UTILIDAD NETA', f"RD$ {income_data.get('utilidad_neta', 0):,.2f}"],
            ]
            
            # Crear tabla
            table = Table(table_data, colWidths=[4*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
                ('FONTNAME', (0, 9), (-1, 9), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 14),
                ('LINEABOVE', (0, 5), (-1, 5), 1.5, colors.black),
                ('LINEABOVE', (0, 9), (-1, 9), 1.5, colors.black),
                ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#EFF6FF')),
            ]))
            
            story.append(table)
            
            # Generar PDF
            doc.build(story)
            return True
            
        except Exception as e:
            print(f"[PDF_GENERATOR] Error generando Estado de Resultados: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_journal_entry_pdf(
        self,
        filename: str,
        entry_data: dict
    ) -> bool:
        """
        Genera PDF de un comprobante de asiento contable.
        
        Args:
            filename: Ruta donde guardar el PDF
            entry_data: Datos del asiento con estructura:
                {
                    'entry_id': str,
                    'date': datetime,
                    'reference': str,
                    'description': str,
                    'lines': [
                        {
                            'account_name': str,
                            'account_code': str,
                            'debit': float,
                            'credit': float,
                            'description': str
                        }
                    ]
                }
        
        Returns:
            True si se generó exitosamente
        """
        try:
            doc = SimpleDocTemplate(filename, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Título
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1E40AF'),
                alignment=TA_CENTER,
                spaceAfter=12
            )
            
            story.append(Paragraph(self.company_name, title_style))
            story.append(Paragraph("COMPROBANTE DE ASIENTO CONTABLE", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Información del asiento
            info_data = [
                ['Asiento No.:', entry_data.get('entry_id', '')],
                ['Fecha:', entry_data.get('date', '')],
                ['Referencia:', entry_data.get('reference', '')],
                ['Descripción:', entry_data.get('description', '')],
            ]
            
            info_table = Table(info_data, colWidths=[1.5*inch, 4.5*inch])
            info_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 0.2*inch))
            
            # Tabla de líneas
            lines_data = [['Cuenta', 'Código', 'Descripción', 'Débito', 'Crédito']]
            
            total_debit = 0.0
            total_credit = 0.0
            
            for line in entry_data.get('lines', []):
                debit = line.get('debit', 0.0)
                credit = line.get('credit', 0.0)
                total_debit += debit
                total_credit += credit
                
                lines_data.append([
                    line.get('account_name', ''),
                    line.get('account_code', ''),
                    line.get('description', ''),
                    f"RD$ {debit:,.2f}" if debit > 0 else '',
                    f"RD$ {credit:,.2f}" if credit > 0 else ''
                ])
            
            # Totales
            lines_data.append(['', '', 'TOTALES', f"RD$ {total_debit:,.2f}", f"RD$ {total_credit:,.2f}"])
            
            # Crear tabla
            lines_table = Table(
                lines_data,
                colWidths=[2*inch, 1*inch, 2*inch, 1.25*inch, 1.25*inch]
            )
            lines_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (3, 0), (4, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
            ]))
            
            story.append(lines_table)
            
            # Verificación
            balance_check = abs(total_debit - total_credit)
            story.append(Spacer(1, 0.2*inch))
            
            if balance_check < 0.01:
                status_text = "✓ Asiento cuadrado (Débito = Crédito)"
                status_color = colors.green
            else:
                status_text = f"✗ Asiento descuadrado (Diferencia: RD$ {balance_check:,.2f})"
                status_color = colors.red
            
            status_style = ParagraphStyle(
                'Status',
                parent=styles['Normal'],
                fontSize=12,
                textColor=status_color,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            story.append(Paragraph(status_text, status_style))
            
            # Generar PDF
            doc.build(story)
            return True
            
        except Exception as e:
            print(f"[PDF_GENERATOR] Error generando comprobante de asiento: {e}")
            import traceback
            traceback.print_exc()
            return False
