import os
import io
import glob
import shutil
import tempfile
import logging
import math
import datetime

import pandas as pd
from fpdf import FPDF
from PIL import Image
from pypdf import PdfWriter, PdfReader

# Logger config
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)



# --- DESPUÉS DE LOS IMPORTS Y ANTES DE COLORS ---

def format_date_for_report(date_val) -> str:
    """
    Formatea una fecha a string YYYY-MM-DD (sin hora).
    Maneja datetime, date, strings y timestamps de Firestore/Firebase.
    """
    if not date_val:
        return ""
    
    # Manejar DatetimeWithNanoseconds de Firestore
    if hasattr(date_val, 'date') and callable(date_val.date):
        try:
            return date_val.date().strftime("%Y-%m-%d")
        except: 
            pass
    
    # datetime.datetime
    if isinstance(date_val, datetime.datetime):
        return date_val. strftime("%Y-%m-%d")
    
    # datetime. date
    if isinstance(date_val, datetime.date):
        return date_val.strftime("%Y-%m-%d")
    
    # String:  extraer primeros 10 caracteres si tiene formato ISO
    date_str = str(date_val).strip()
    if len(date_str) >= 10 and date_str[4] == '-' and date_str[7] == '-':
        return date_str[:10]
    
    return date_str


import os
import io
import glob
import shutil
import tempfile
import logging
import math
import datetime

import pandas as pd
from fpdf import FPDF
from PIL import Image
from pypdf import PdfWriter, PdfReader

# Logger config
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# --- UTILS ---
def format_date_for_report(date_val) -> str:
    """Formatea una fecha a string YYYY-MM-DD."""
    if not date_val:
        return ""
    if hasattr(date_val, 'date') and callable(date_val.date):
        try: return date_val.date().strftime("%Y-%m-%d")
        except: pass
    if isinstance(date_val, datetime.datetime):
        return date_val.strftime("%Y-%m-%d")
    if isinstance(date_val, datetime.date):
        return date_val.strftime("%Y-%m-%d")
    date_str = str(date_val).strip()
    if len(date_str) >= 10 and date_str[4] == '-' and date_str[7] == '-':
        return date_str[:10]
    return date_str

# --- COLORS ---
COLORS = {
    'white': (255, 255, 255),
    'slate_50': (248, 250, 252),
    'slate_100': (241, 245, 249),
    'slate_200': (226, 232, 240),
    'slate_400': (148, 163, 184),
    'slate_500': (100, 116, 139),
    'slate_600': (71, 85, 105),
    'slate_700': (51, 65, 85),
    'slate_800': (30, 41, 59),
    'slate_900': (15, 23, 42),
    'emerald_50': (236, 253, 245),
    'emerald_500': (16, 185, 129),
    'emerald_600': (5, 150, 105),
    'red_50': (254, 242, 242),
    'red_500': (239, 68, 68),
    'red_600': (220, 38, 38),
    'blue_50': (239, 246, 255),
    'blue_500': (59, 130, 246),
    'blue_600': (37, 99, 235),
    'indigo_900': (49, 46, 129),
}

class ModernPDF(FPDF):
    def __init__(self, orientation='P', unit='mm', format='A4', company_name="", report_title="", report_period=""):
        super().__init__(orientation, unit, format)
        self.company_name = company_name
        self.report_title = report_title
        self.report_period = report_period
        self.set_auto_page_break(auto=True, margin=15)
        self.alias_nb_pages()
        self.set_margins(15, 15, 15)

    def set_color_rgb(self, rgb_tuple):
        self.set_draw_color(*rgb_tuple)
        self.set_fill_color(*rgb_tuple)
        self.set_text_color(*rgb_tuple)

    def set_text_color_rgb(self, rgb_tuple):
        self.set_text_color(*rgb_tuple)
        
    def set_fill_color_rgb(self, rgb_tuple):
        self.set_fill_color(*rgb_tuple)
        
    def set_draw_color_rgb(self, rgb_tuple):
        self.set_draw_color(*rgb_tuple)

    def rounded_rect(self, x, y, w, h, r, style='D', corners='1234'):
        k = 0.26878
        if style == 'F': op = 'f'
        elif style == 'FD' or style == 'DF': op = 'B'
        else: op = 'S'
        hp = self.h
        self._out('%.2f %.2f m' % ((x + r) * self.k, (hp - y) * self.k))
        if '2' in corners:
            xc = x + w - r
            yc = y + r
            self._out('%.2f %.2f l' % (xc * self.k, (hp - y) * self.k))
            self._out('%.2f %.2f %.2f %.2f %.2f %.2f c' % ((xc + r * k) * self.k, (hp - y) * self.k, (x + w) * self.k, (hp - (yc - r * k)) * self.k, (x + w) * self.k, (hp - yc) * self.k))
        else: self._out('%.2f %.2f l' % ((x + w) * self.k, (hp - y) * self.k))
        if '3' in corners:
            xc = x + w - r
            yc = y + h - r
            self._out('%.2f %.2f l' % ((x + w) * self.k, (hp - yc) * self.k))
            self._out('%.2f %.2f %.2f %.2f %.2f %.2f c' % ((x + w) * self.k, (hp - (yc + r * k)) * self.k, (xc + r * k) * self.k, (hp - (y + h)) * self.k, xc * self.k, (hp - (y + h)) * self.k))
        else: self._out('%.2f %.2f l' % ((x + w) * self.k, (hp - (y + h)) * self.k))
        if '4' in corners:
            xc = x + r
            yc = y + h - r
            self._out('%.2f %.2f l' % (xc * self.k, (hp - (y + h)) * self.k))
            self._out('%.2f %.2f %.2f %.2f %.2f %.2f c' % ((xc - r * k) * self.k, (hp - (y + h)) * self.k, x * self.k, (hp - (yc + r * k)) * self.k, x * self.k, (hp - yc) * self.k))
        else: self._out('%.2f %.2f l' % (x * self.k, (hp - (y + h)) * self.k))
        if '1' in corners:
            xc = x + r
            yc = y + r
            self._out('%.2f %.2f l' % (x * self.k, (hp - yc) * self.k))
            self._out('%.2f %.2f %.2f %.2f %.2f %.2f c' % (x * self.k, (hp - (yc - r * k)) * self.k, (xc - r * k) * self.k, (hp - y) * self.k, xc * self.k, (hp - y) * self.k))
        else: self._out('%.2f %.2f l' % (x * self.k, (hp - y) * self.k))
        self._out(op)

    def draw_badge(self, text, x, y, bg_color, text_color):
        self.set_font('Arial', 'B', 7)
        w = self.get_string_width(text) + 6
        h = 5
        self.set_fill_color_rgb(bg_color)
        self.set_text_color_rgb(text_color)
        self.set_draw_color_rgb(bg_color)
        self.rounded_rect(x, y, w, h, 2, 'DF')
        self.set_xy(x, y)
        self.cell(w, h, text, 0, 0, 'C')
        
    def header(self):
        # Header Corregido y Alineado
        if self.page_no() == 1:
            self.set_fill_color_rgb(COLORS['slate_900'])
            self.rounded_rect(15, 12, 10, 10, 2, 'F')
            
            # Anchos y posiciones dinámicas
            page_width = self.w - 30 
            right_width = 90  # Ancho fijo para bloque derecho
            left_width = page_width - right_width - 15 

            # Izquierda
            self.set_xy(28, 12)
            self.set_font('Arial', 'B', 14)
            self.set_text_color_rgb(COLORS['slate_900'])
            self.cell(left_width, 6, "Gestión Facturas PRO", 0, 0, 'L')
            
            self.set_xy(28, 19)
            self.set_font('Arial', '', 10)
            self.set_text_color_rgb(COLORS['slate_500'])
            self.cell(left_width, 5, self.report_title[:55], 0, 0, 'L')
            
            # Derecha
            right_x = self.w - 15 - right_width
            self.set_xy(right_x, 12)
            self.set_font('Arial', 'B', 8)
            self.set_text_color_rgb(COLORS['slate_400'])
            self.cell(right_width, 4, "EMPRESA / PERIODO", 0, 1, 'R')
            
            self.set_x(right_x)
            self.set_font('Arial', 'B', 10)
            self.set_text_color_rgb(COLORS['slate_800'])
            self.cell(right_width, 5, self.company_name[:40], 0, 1, 'R')
            
            self.set_x(right_x)
            self.set_font('Arial', '', 9)
            self.set_text_color_rgb(COLORS['slate_500'])
            self.cell(right_width, 5, self.report_period, 0, 1, 'R')
            
            self.set_y(32)
            self.set_draw_color_rgb(COLORS['slate_200'])
            self.line(15, 32, self.w - 15, 32)
            self.ln(8)
        else:
            self.set_font('Arial', 'I', 8)
            self.set_text_color_rgb(COLORS['slate_400'])
            self.cell(0, 10, f"{self.report_title} - {self.report_period}", 0, 0, 'R')
            self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', '', 8)
        self.set_text_color_rgb(COLORS['slate_400'])
        self.set_draw_color_rgb(COLORS['slate_100'])
        self.line(15, self.get_y() - 2, self.w - 15, self.get_y() - 2)
        self.cell(0, 10, f'Confidencial - Página {self.page_no()}/{{nb}}', 0, 0, 'C')


def generate_professional_pdf(report_data, save_path, company_name, month, year, attachment_base_path=None):
    """
    Genera el Reporte Mensual estilo Dashboard moderno.
    """
    temp_files = []

    def find_attachment_fullpath(base_path, relative_path, invoice):
        try:
            if invoice and invoice.get("attachment_resolved"):
                ar = invoice.get("attachment_resolved")
                if ar and os.path.exists(ar): return ar
        except:  pass
        if not relative_path:  return None
        rel = str(relative_path).strip()
        if not rel: return None
        if os.path.isabs(rel) and os.path.exists(rel): return rel
        candidates = []
        if base_path:
            candidates.append(os.path.join(base_path, rel))
            candidates.append(os.path. join(base_path, os.path.basename(rel)))
        try:
            comp = invoice.get("company_id") or invoice.get("company")
            if comp and base_path:  candidates.append(os.path. join(base_path, str(comp), rel))
        except: pass
        try:
            if base_path: 
                pattern = os.path.join(base_path, "**", os.path.basename(rel))
                matches = glob.glob(pattern, recursive=True)
                if matches:  return matches[0]
        except:  pass
        return None

    try:
        # Temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_report:
            temp_report_path = temp_report.name
            temp_files.append(temp_report_path)

        pdf = ModernPDF(
            orientation='P',
            company_name=company_name,
            report_title="Reporte Mensual de Facturación",
            report_period=f"{month}/{year}",
        )
        pdf.add_page()

        summary = report_data. get('summary', {}) if report_data else {}
        
        # -----------------------------------------------------------------
        # KPI CARDS (Grid de 3)
        # -----------------------------------------------------------------
        full_width = pdf.w - 30
        card_gap = 5
        card_w = (full_width - (card_gap * 2)) / 3
        card_h = 25
        
        y_start = pdf.get_y()
        
        kpis = [
            {
                "label": "TOTAL INGRESOS", 
                "value": summary. get('total_ingresos', 0.0), 
                "color_accent":  COLORS['emerald_500'],
                "icon": "+" 
            },
            {
                "label": "TOTAL GASTOS", 
                "value":  summary.get('total_gastos', 0.0), 
                "color_accent": COLORS['red_500'],
                "icon": "-"
            },
            {
                "label": "BALANCE NETO", 
                "value": summary.get('total_neto', 0.0), 
                "color_accent": COLORS['slate_800'],
                "icon": "="
            }
        ]
        
        for i, kpi in enumerate(kpis):
            x = 15 + (card_w + card_gap) * i
            
            pdf.set_fill_color_rgb(COLORS['white'])
            pdf.set_draw_color_rgb(COLORS['slate_200'])
            pdf.rounded_rect(x, y_start, card_w, card_h, 2, 'DF')
            
            pdf.set_fill_color_rgb(kpi['color_accent'])
            pdf.rect(x, y_start, 1.5, card_h, 'F')
            
            pdf.set_xy(x + 4, y_start + 4)
            pdf.set_font('Arial', 'B', 7)
            pdf.set_text_color_rgb(COLORS['slate_500'])
            pdf.cell(card_w - 5, 4, kpi['label'], 0, 1, 'L')
            
            pdf.set_xy(x + 4, y_start + 12)
            pdf.set_font('Arial', 'B', 12)
            pdf.set_text_color_rgb(COLORS['slate_800'])
            val_str = f"RD$ {kpi['value']: ,.2f}"
            pdf. cell(card_w - 5, 6, val_str, 0, 1, 'L')

        pdf.set_y(y_start + card_h + 8)

        # -----------------------------------------------------------------
        # ITBIS MINI CARDS
        # -----------------------------------------------------------------
        mini_card_h = 12
        itbis_data = [
            ("ITBIS Ventas", summary.get('itbis_ingresos', 0.0), COLORS['slate_50']),
            ("ITBIS Compras", summary.get('itbis_gastos', 0.0), COLORS['slate_50']),
            ("ITBIS Neto", summary.get('itbis_neto', 0.0), COLORS['blue_50'])
        ]
        
        y_mini = pdf.get_y()
        for i, (label, val, bg) in enumerate(itbis_data):
            x = 15 + (card_w + card_gap) * i
            
            pdf.set_fill_color_rgb(bg)
            pdf.set_draw_color_rgb(COLORS['slate_100'])
            pdf.rounded_rect(x, y_mini, card_w, mini_card_h, 2, 'DF')
            
            pdf.set_xy(x + 3, y_mini + 3)
            pdf.set_font('Arial', '', 7)
            pdf.set_text_color_rgb(COLORS['slate_500'])
            pdf.cell(card_w/2, 6, label, 0, 0, 'L')
            
            pdf.set_font('Arial', 'B', 8)
            pdf.set_text_color_rgb(COLORS['slate_700'])
            pdf.cell((card_w/2)-6, 6, f"{val:,.2f}", 0, 0, 'R')
            
        pdf.set_y(y_mini + mini_card_h + 10)

        # -----------------------------------------------------------------
        # TABLAS
        # -----------------------------------------------------------------
        def draw_modern_table(title, headers, data, col_widths_pct, accent_color):
            pdf.set_font('Arial', 'B', 10)
            pdf.set_text_color_rgb(COLORS['slate_800'])
            
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.set_fill_color_rgb(accent_color)
            pdf.rounded_rect(x, y+1, 1, 4, 0.5, 'F')
            
            pdf.set_x(x + 3)
            pdf.cell(0, 6, title. upper(), 0, 1, 'L')
            pdf.ln(2)
            
            full_w = pdf.w - 30
            col_widths = [(pct/100)*full_w for pct in col_widths_pct]
            
            pdf.set_font('Arial', 'B', 7)
            pdf.set_text_color_rgb(COLORS['slate_500'])
            pdf.set_fill_color_rgb(COLORS['slate_50'])
            pdf.set_draw_color_rgb(COLORS['slate_200'])
            
            pdf.rect(15, pdf.get_y(), full_w, 8, 'F')
            
            start_x = 15
            for i, h_text in enumerate(headers):
                align = 'R' if i >= 3 else 'L'
                pdf.set_xy(start_x, pdf.get_y())
                pdf.cell(col_widths[i], 8, h_text, 0, 0, align)
                start_x += col_widths[i]
            pdf.ln(8)
            
            pdf.set_font('Arial', '', 8)
            pdf.set_text_color_rgb(COLORS['slate_600'])
            
            for row_idx, row in enumerate(data):
                pdf.set_draw_color_rgb(COLORS['slate_50'])
                h_row = 8
                
                if pdf.get_y() > 270:
                    pdf.add_page()
                    pdf.set_font('Arial', 'B', 7)
                    pdf.set_text_color_rgb(COLORS['slate_500'])
                    pdf.set_fill_color_rgb(COLORS['slate_50'])
                    pdf.rect(15, pdf.get_y(), full_w, 8, 'F')
                    start_x = 15
                    for i, h_text in enumerate(headers):
                        align = 'R' if i >= 3 else 'L'
                        pdf.set_xy(start_x, pdf.get_y())
                        pdf.cell(col_widths[i], 8, h_text, 0, 0, align)
                        start_x += col_widths[i]
                    pdf.ln(8)
                    pdf.set_font('Arial', '', 8)
                    pdf. set_text_color_rgb(COLORS['slate_600'])

                start_x = 15
                for i, cell_val in enumerate(row):
                    align = 'R' if i >= 3 else 'L'
                    
                    if i == 4:  
                        pdf.set_font('Arial', 'B', 8)
                        pdf.set_text_color_rgb(COLORS['slate_800'])
                    else:
                        pdf.set_font('Arial', '', 8)
                        pdf.set_text_color_rgb(COLORS['slate_600'])
                        
                    pdf.set_xy(start_x, pdf.get_y())
                    pdf.cell(col_widths[i], h_row, str(cell_val), 'B', 0, align)
                    start_x += col_widths[i]
                pdf.ln(h_row)

        def _safe_list(lst):
            n = []
            for x in lst or []:
                if isinstance(x, dict): n.append(x)
                else: 
                    try: n.append(dict(x)) 
                    except: pass
            return n

        # ✅ Datos Facturas Emitidas - ITBIS corregido sin doble multiplicación
        inv_emitted = _safe_list(report_data. get('emitted_invoices', []))
        data_em = []
        for f in inv_emitted:
            # Obtener valores ya convertidos a RD$ (sin multiplicar nuevamente)
            # Priorizar campos _rd que ya están en pesos dominicanos
            itbis_rd = float(f.get('itbis_rd') or f.get('itbis', 0.0) or 0.0)
            total_rd = float(f.get('total_amount_rd') or f.get('total_amount', 0.0) or 0.0)
            
            # Obtener moneda y valores originales para mostrar
            currency = f.get('currency', 'RD$')
            itbis_orig = f.get('itbis_original_currency')
            total_orig = f.get('total_amount_original_currency')
            
            # Si hay moneda extranjera, mostrar ambos valores
            if currency not in ['RD$', 'DOP'] and itbis_orig is not None:
                itbis_display = f"{currency} {float(itbis_orig):,.2f} / RD$ {itbis_rd:,.2f}"
                total_display = f"{currency} {float(total_orig):,.2f} / RD$ {total_rd:,.2f}"
            else:
                itbis_display = f"RD$ {itbis_rd:,.2f}"
                total_display = f"RD$ {total_rd:,.2f}"
            
            data_em.append([
                format_date_for_report(f.get('invoice_date')),
                f.get('invoice_number', ''),
                f.get('third_party_name', '')[: 25],
                itbis_display,
                total_display
            ])
            
        draw_modern_table(
            "Últimas Facturas Emitidas",
            ['Fecha', 'NCF', 'Cliente', 'ITBIS', 'Total'],
            data_em,
            [12, 18, 25, 22, 23],
            COLORS['emerald_500']
        )
        
        pdf.ln(8)
        
        # ✅ Datos Gastos - ITBIS corregido sin doble multiplicación
        inv_expenses = _safe_list(report_data.get('expense_invoices', []))
        data_ex = []
        for f in inv_expenses:
            # Obtener valores ya convertidos a RD$ (sin multiplicar nuevamente)
            itbis_rd = float(f.get('itbis_rd') or f.get('itbis', 0.0) or 0.0)
            total_rd = float(f.get('total_amount_rd') or f.get('total_amount', 0.0) or 0.0)
            
            # Obtener moneda y valores originales
            currency = f.get('currency', 'RD$')
            itbis_orig = f.get('itbis_original_currency')
            total_orig = f.get('total_amount_original_currency')
            
            # Si hay moneda extranjera, mostrar ambos valores
            if currency not in ['RD$', 'DOP'] and itbis_orig is not None:
                itbis_display = f"{currency} {float(itbis_orig):,.2f} / RD$ {itbis_rd:,.2f}"
                total_display = f"{currency} {float(total_orig):,.2f} / RD$ {total_rd:,.2f}"
            else:
                itbis_display = f"RD$ {itbis_rd:,.2f}"
                total_display = f"RD$ {total_rd:,.2f}"
            
            data_ex. append([
                format_date_for_report(f.get('invoice_date')),
                f.get('invoice_number', ''),
                f.get('third_party_name', '')[:25],
                itbis_display,
                total_display
            ])
            
        draw_modern_table(
            "Gastos Registrados",
            ['Fecha', 'NCF', 'Proveedor', 'ITBIS', 'Total'],
            data_ex,
            [12, 18, 25, 22, 23],
            COLORS['red_500']
        )

        pdf.output(temp_report_path)

        # ---------------------------------------------------------
        # FASE 2: UNIÓN DE ANEXOS
        # ---------------------------------------------------------
        merger = PdfWriter()
        try:
            merger.append(temp_report_path)
        except: pass
        
        attachments_candidates = []
        if report_data and report_data.get('ordered_attachments') is not None:
             attachments_candidates = report_data.get('ordered_attachments')
        else:
             for f in inv_emitted + inv_expenses:
                 res = f.get('attachment_resolved')
                 orig = f.get('attachment_path') or f.get('attachment')
                 if res or orig:
                     nf = dict(f)
                     nf['attachment_resolved'] = res
                     nf['attachment_original'] = orig
                     attachments_candidates.append(nf)
                     
        for invoice in attachments_candidates:
            try:
                rel = invoice.get('attachment_original') or ''
                full_path = find_attachment_fullpath(attachment_base_path, rel, invoice)
                if not full_path:  continue
                
                if full_path. lower().endswith('.pdf'):
                    try:
                        merger.append(PdfReader(full_path, strict=False))
                    except:  pass
                elif full_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=". pdf") as timg:
                        timg_p = timg.name
                        temp_files.append(timg_p)
                    
                    pdf_img = ModernPDF(orientation='P', report_title="Anexo", report_period=invoice.get('invoice_number', ''))
                    pdf_img.add_page()
                    try:
                        with Image.open(full_path) as im:
                            w, h = im.size
                            aspect = w / h
                            avail_w = pdf_img.w - 30
                            avail_h = pdf_img.h - 40
                            disp_w = avail_w
                            disp_h = disp_w / aspect
                            if disp_h > avail_h:
                                disp_h = avail_h
                                disp_w = disp_h * aspect
                            pdf_img.image(full_path, x=15, y=30, w=disp_w, h=disp_h)
                        pdf_img.output(timg_p)
                        merger.append(PdfReader(timg_p, strict=False))
                    except: pass
            except:  pass

        with open(save_path, "wb") as f_out:
            merger.write(f_out)
            
        return True, "Reporte generado con éxito."

    except Exception as e: 
        logger.exception("Error generando PDF mensual")
        return False, str(e)
    finally:
        for tf in temp_files:
            try:  os.remove(tf)
            except: pass

def generate_retention_pdf(save_path, company_name, period_str, results_data, selected_invoices):
    """
    Genera el 'Estado de Retención' estilo extracto bancario. 
    """
    try:
        company_display = (
            results_data.get("company_name")
            or results_data.get("empresa")
            or results_data. get("company_label")
            or results_data.get("company")
            or str(company_name)
        )

        pdf = ModernPDF(
            orientation='P',
            company_name=company_display,
            report_title="Estado de Retención",
            report_period=period_str
        )
        pdf.add_page()

        # --- HEADER "CLASSIC BANK" ---
        pdf.set_y(15)
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color_rgb(COLORS['slate_900'])
        pdf.cell(0, 8, "Estado de Retención", 0, 1, 'L')
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color_rgb(COLORS['slate_500'])
        pdf.cell(0, 6, "Cálculo de impuestos retenidos a terceros", 0, 1, 'L')
        
        ref_code = results_data.get("ref_code", f"RET-{period_str. replace(' ','-')}")
        pdf.set_xy(pdf.w - 70, 15)
        pdf.set_fill_color_rgb(COLORS['slate_50'])
        pdf.rounded_rect(pdf.w - 70, 15, 55, 14, 2, 'F')
        
        pdf.set_xy(pdf.w - 68, 17)
        pdf.set_font('Arial', 'B', 8)
        pdf.set_text_color_rgb(COLORS['slate_600'])
        pdf.cell(50, 4, f"Ref: {ref_code}", 0, 1, 'R')
        pdf.set_x(pdf.w - 68)
        pdf.set_font('Arial', '', 8)
        pdf.set_text_color_rgb(COLORS['slate_400'])
        pdf.cell(50, 4, f"Corte: {datetime.date.today()}", 0, 1, 'R')
        
        pdf.ln(15)
        
        # --- STATEMENT CARD (DARK) ---
        card_h = 45
        card_w = pdf.w - 30
        x = 15
        y = pdf.get_y()
        
        pdf.set_fill_color_rgb(COLORS['slate_900'])
        pdf.rounded_rect(x, y, card_w, card_h, 4, 'F')
        
        base = float(results_data.get("total_general_rd", 0.0) or 0.0)
        total_ret = float(results_data.get("total_a_retener", 0.0) or 0.0)
        count = int(results_data.get("num_invoices", len(selected_invoices)))
        norma = results_data.get("norm_label", "Norma 02-05")
        
        pdf.set_xy(x+10, y+8)
        pdf.set_font('Arial', 'B', 8)
        pdf.set_text_color_rgb(COLORS['slate_400'])
        pdf.cell(80, 5, "MONTO BASE CALCULADO", 0, 1, 'L')
        
        pdf.set_x(x+10)
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color_rgb(COLORS['white'])
        pdf.cell(80, 8, f"RD$ {base:,.2f}", 0, 1, 'L')
        
        bx = x+10
        by = y+25
        pdf.draw_badge(f"{count} Facturas", bx, by, COLORS['slate_700'], COLORS['slate_100'])
        pdf.draw_badge(norma, bx+30, by, COLORS['slate_700'], COLORS['slate_100'])
        
        pdf.set_draw_color_rgb(COLORS['slate_700'])
        pdf.line(x + (card_w/2), y+5, x + (card_w/2), y+card_h-5)
        
        pdf.set_xy(x + (card_w/2) + 10, y+8)
        pdf.set_font('Arial', 'B', 8)
        pdf.set_text_color_rgb(COLORS['emerald_500'])
        pdf.cell(80, 5, "TOTAL A RETENER (PAGAR)", 0, 1, 'L')
        
        pdf.set_xy(x + (card_w/2) + 10, y+14)
        pdf.set_font('Arial', 'B', 24)
        pdf.set_text_color_rgb(COLORS['white'])
        pdf.cell(80, 12, f"RD$ {total_ret:,.2f}", 0, 1, 'L')
        
        pdf.set_xy(x + (card_w/2) + 10, y+28)
        pdf.set_font('Arial', '', 7)
        pdf.set_text_color_rgb(COLORS['slate_400'])
        pdf.cell(80, 4, "Remitir a DGII antes del día 17.", 0, 1, 'L')
        
        pdf.set_y(y + card_h + 10)
        
        # --- DESGLOSE ---
        pdf.set_fill_color_rgb(COLORS['white'])
        pdf.set_draw_color_rgb(COLORS['slate_200'])
        pdf.rounded_rect(x, pdf.get_y(), card_w, 35, 2, 'S')
        
        y_d = pdf.get_y() + 4
        pdf.set_xy(x+5, y_d)
        pdf.set_font('Arial', 'B', 9)
        pdf.set_text_color_rgb(COLORS['slate_800'])
        pdf.cell(0, 5, "Desglose del Cálculo", 0, 1, 'L')
        pdf.set_draw_color_rgb(COLORS['slate_100'])
        pdf.line(x+5, pdf.get_y()+1, x+card_w-5, pdf.get_y()+1)
        
        itbis_tot = float(results_data.get("total_itbis_rd", 0.0) or 0.0)
        ret_itbis = float(results_data.get("ret_itbis", 0.0) or 0.0)
        
        lines = [
            ("ITBIS Total Facturado", f"RD$ {itbis_tot:,.2f}", COLORS['slate_600']),
            ("Retención ITBIS (100% Norma)", f"- RD$ {ret_itbis:,.2f}", COLORS['red_600']),
        ]
        
        y_line = pdf.get_y() + 4
        for label, val, color in lines:
            pdf.set_xy(x+5, y_line)
            pdf.set_font('Arial', '', 8)
            pdf.set_text_color_rgb(COLORS['slate_500'])
            pdf.cell(100, 5, label, 0, 0, 'L')
            
            pdf.set_font('Arial', 'B', 8)
            pdf.set_text_color_rgb(color)
            pdf.cell(card_w - 110, 5, val, 0, 0, 'R')
            y_line += 6
            
        pdf.line(x+5, y_line+1, x+card_w-5, y_line+1)
        pdf.set_xy(x+5, y_line+3)
        pdf.set_font('Arial', 'B', 9)
        pdf.set_text_color_rgb(COLORS['slate_900'])
        pdf.cell(100, 5, "Total Retenido", 0, 0, 'L')
        pdf.cell(card_w - 110, 5, f"RD$ {total_ret:,.2f}", 0, 0, 'R')
        
        pdf.set_y(y_d + 35 + 8)
        
        # --- TABLA DOCUMENTOS ---
        pdf.set_font('Arial', 'B', 8)
        pdf.set_text_color_rgb(COLORS['slate_500'])
        pdf.cell(0, 6, "DOCUMENTOS INCLUIDOS", 0, 1, 'L')
        
        headers = ["Fecha", "Proveedor", "NCF", "Base Imp.", "ITBIS", "Retención"]
        widths = [20, 60, 30, 25, 20, 25]
        
        pdf.set_fill_color_rgb(COLORS['slate_50'])
        pdf.set_text_color_rgb(COLORS['slate_500'])
        pdf.set_font('Arial', 'B', 7)
        pdf.rect(15, pdf.get_y(), card_w, 8, 'F')
        
        start_x = 15
        for i, h in enumerate(headers):
            align = 'R' if i >= 3 else 'L'
            pdf.set_xy(start_x, pdf.get_y())
            pdf.cell(widths[i], 8, h, 0, 0, align)
            start_x += widths[i]
        pdf.ln(8)
        
        pdf.set_font('Arial', '', 7)
        pdf.set_text_color_rgb(COLORS['slate_600'])
        
        # ✅ Rows - FECHA CORREGIDA
        for inv in selected_invoices:
            base_rd = float(inv.get("total_amount_rd", 0.0) or 0.0)
            rate = float(inv.get("exchange_rate", 1.0) or 1.0)
            itbis_rd = float(inv.get("itbis", 0.0) or 0.0) * rate
            ret_row = 0.0
            if itbis_tot > 0:
                ret_row = (itbis_rd / itbis_tot) * total_ret
            
            vals = [
                format_date_for_report(inv.get("invoice_date")),  # ✅ CORREGIDO
                str(inv.get("third_party_name", ""))[:35],
                str(inv.get("invoice_number", "")),
                f"{base_rd:,.2f}",
                f"{itbis_rd:,.2f}",
                f"{ret_row: ,.2f}"
            ]
            
            start_x = 15
            for i, v in enumerate(vals):
                align = 'R' if i >= 3 else 'L'
                pdf.set_xy(start_x, pdf.get_y())
                
                if i == 5: 
                    pdf.set_fill_color_rgb(COLORS['slate_50'])
                    pdf.cell(widths[i], 6, v, 0, 0, align, fill=True)
                    pdf.set_font('Arial', 'B', 7)
                else:
                    pdf.cell(widths[i], 6, v, 0, 0, align)
                    pdf.set_font('Arial', '', 7)
                
                start_x += widths[i]
            pdf.ln(6)
            
        pdf.output(save_path)
        return True, "PDF generado."

    except Exception as e: 
        logger.exception("Error Retencion PDF")
        return False, str(e)
    

def generate_advanced_retention_pdf(save_path, company_name, period_str, summary_data, selected_invoices):
    """
    Genera el reporte multi-moneda.
    CORREGIDO: Coordenadas dinámicas para evitar solapamiento con header.
    """
    try:
        pdf = ModernPDF(orientation='L', company_name=company_name, report_title="Reporte Impuestos Multi-Moneda", report_period=period_str)
        pdf.add_page()
        
        full_w = pdf.w - 30
        
        # --- GLOBAL SUMMARY BAR ---
        # Usamos coordenadas relativas para no pisar el header
        start_y = pdf.get_y()
        if start_y < 35: start_y = 35 # Seguridad extra
        
        bar_height = 22
        pdf.set_fill_color_rgb(COLORS['indigo_900'])
        pdf.rounded_rect(15, start_y, full_w, bar_height, 3, 'F')
        
        grand_total = summary_data.get('grand_total_rd', 0.0)
        
        # Texto dentro de la barra usando start_y
        pdf.set_xy(20, start_y + 5)
        pdf.set_font('Arial', 'B', 8)
        pdf.set_text_color_rgb(COLORS['blue_50'])
        pdf.cell(100, 4, "IMPUESTO TOTAL ESTIMADO (GLOBAL)", 0, 1, 'L')
        
        pdf.set_xy(20, start_y + 11)
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color_rgb(COLORS['white'])
        pdf.cell(100, 8, f"RD$ {grand_total:,.2f}", 0, 1, 'L')
        
        # Mover el cursor debajo de la barra
        pdf.set_y(start_y + bar_height + 10)
        
        # --- GROUP BY CURRENCY ---
        grouped = {}
        for inv in selected_invoices:
            curr = inv.get('currency', 'RD$')
            if curr not in grouped:  grouped[curr] = []
            grouped[curr].append(inv)
            
        currency_map = {
            'USD': {'name': 'Dólar Estadounidense', 'badge':  COLORS['emerald_50']},
            'EUR': {'name': 'Euro', 'badge': COLORS['blue_50']},
            'RD$': {'name': 'Peso Dominicano', 'badge': COLORS['slate_50']}
        }
        
        for curr, invoices in grouped.items():
            if pdf.get_y() > 160: 
                pdf.add_page()
                pdf.ln(5)

            meta = currency_map.get(curr, {'name': curr, 'badge': COLORS['slate_50']})
            pdf.draw_badge(f"{curr} - {meta['name']}", 15, pdf.get_y(), meta['badge'], COLORS['slate_700'])
            
            sub_imp = sum(x.get('total_imp_orig', 0) for x in invoices)
            pdf.set_xy(70, pdf.get_y())
            pdf.set_font('Arial', 'B', 9)
            pdf.set_text_color_rgb(COLORS['slate_600'])
            pdf.cell(100, 5, f"Impuestos: {sub_imp:,.2f} {curr}", 0, 1, 'L')
            
            pdf.ln(8)
            
            headers = ["Fecha", "Factura / Empresa", "Tasa", f"Total ({curr})", f"Imp. ({curr})", "Imp. (RD$)"]
            widths = [25, 90, 20, 35, 35, 40]
            
            pdf.set_fill_color_rgb(COLORS['slate_50'])
            pdf.set_text_color_rgb(COLORS['slate_500'])
            pdf.set_font('Arial', '', 8)
            pdf.rect(15, pdf.get_y(), full_w, 8, 'F')
            
            start_x = 15
            for i, h in enumerate(headers):
                align = 'R' if i >= 2 else 'L'
                pdf.set_xy(start_x, pdf.get_y())
                pdf.cell(widths[i], 8, h, 0, 0, align)
                start_x += widths[i]
            pdf.ln(8)
            
            pdf.set_font('Arial', '', 8)
            pdf.set_text_color_rgb(COLORS['slate_600'])
            
            sub_imp_rd = 0.0
            
            for inv in invoices:
                if pdf.get_y() > 180:  
                    pdf.add_page()
                    pdf.ln(5)
                
                imp_rd = inv.get('total_imp_rd', 0.0)
                sub_imp_rd += imp_rd
                
                vals = [
                    format_date_for_report(inv.get('fecha') or inv.get('invoice_date')),
                    f"{inv.get('no_fact','')} - {inv.get('empresa','')[:30]}",
                    f"{inv.get('exchange_rate',1):.2f}",
                    f"{inv.get('total_orig',0):,.2f}",
                    f"{inv.get('total_imp_orig',0):,.2f}",
                    f"{imp_rd:,.2f}"
                ]
                
                start_x = 15
                for i, v in enumerate(vals):
                    align = 'R' if i >= 2 else 'L'
                    pdf.set_xy(start_x, pdf.get_y())
                    
                    if i == 5:
                        pdf.set_font('Arial', 'B', 8)
                        pdf.set_fill_color_rgb(COLORS['slate_50'])
                        pdf.cell(widths[i], 6, v, 0, 0, align, fill=True)
                        pdf.set_font('Arial', '', 8)
                    elif i == 4:
                        pdf.set_text_color_rgb(COLORS['red_600'])
                        pdf.cell(widths[i], 6, v, 0, 0, align)
                        pdf.set_text_color_rgb(COLORS['slate_600'])
                    else:
                        pdf.cell(widths[i], 6, v, 0, 0, align)
                    start_x += widths[i]
                pdf.ln(6)
            
            pdf.ln(2)
            pdf.set_x(full_w - 95) # Alineado a la derecha
            pdf.set_fill_color_rgb(COLORS['emerald_50'])
            pdf.set_text_color_rgb(COLORS['emerald_600'])
            pdf.set_font('Arial', 'B', 8)
            # Dibujar rect con coordenada actual
            current_x = pdf.w - 15 - 95
            pdf.rounded_rect(current_x, pdf.get_y(), 95, 8, 2, 'F')
            pdf.set_x(current_x)
            pdf.cell(95, 8, f"Subtotal Convertido: RD$ {sub_imp_rd:,.2f}", 0, 1, 'C')
            
            pdf.ln(12)

        # Footer Gran Total
        if pdf.get_y() > 150:  pdf.add_page()
        
        box_width = full_w / 2
        box_x = 15 + (full_w / 4)
        
        pdf.set_fill_color_rgb(COLORS['slate_900'])
        pdf.rounded_rect(box_x, pdf.get_y(), box_width, 30, 3, 'F')
        
        y_f = pdf.get_y()
        pdf.set_xy(box_x + 10, y_f + 5)
        pdf.set_text_color_rgb(COLORS['slate_400'])
        pdf.cell(box_width - 20, 5, "TOTAL A PAGAR (RD$)", 0, 1, 'C')
        
        pdf.set_xy(box_x + 10, y_f + 12)
        pdf.set_font('Arial', 'B', 20)
        pdf.set_text_color_rgb(COLORS['white'])
        pdf.cell(box_width - 20, 10, f"{grand_total:,.2f}", 0, 1, 'C')

        pdf.output(save_path)
        return True, "Reporte Multi-moneda Generado."

    except Exception as e:
        logger.exception("Error Adv PDF")
        return False, str(e)
    
def generate_excel_report(report_data, save_path):
    """Genera reporte Excel (sin cambios de diseño visual, solo datos)."""
    try:
        summary_totals = report_data["summary"]
        resumen_data = {
            "Descripción": ["Total Ingresos (RD$)", "Total ITBIS Ingresos (RD$)", "Total Gastos (RD$)", "Total ITBIS Gastos (RD$)", "ITBIS Neto (RD$)", "Total Neto (RD$)"],
            "Monto": [summary_totals.get("total_ingresos", 0.0), summary_totals.get("itbis_ingresos", 0.0), summary_totals.get("total_gastos", 0.0), summary_totals.get("itbis_gastos", 0.0), summary_totals.get("itbis_neto", 0.0), summary_totals.get("total_neto", 0.0)]
        }
        df_resumen = pd.DataFrame(resumen_data)
        df_ingresos = pd.DataFrame(report_data.get("emitted_invoices", []))
        df_gastos = pd.DataFrame(report_data.get("expense_invoices", []))

        with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
            df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
            df_ingresos.to_excel(writer, sheet_name='Ingresos', index=False)
            df_gastos.to_excel(writer, sheet_name='Gastos', index=False)

        return True, "Excel generado exitosamente."
    except Exception as e:
        return False, f"Error generando Excel: {e}"

def generate_tax_calculation_pdf(report_data, output_path):
    """Wrapper con CORRECCIÓN CRÍTICA DE MONEDA"""
    try:
        calc = report_data.get("calculation", {}) or {}
        invoices = report_data.get("invoices", []) or []

        company_display = calc.get("company_name") or str(calc.get("company_id", ""))
        period_str = f"{calc.get('start_date', '')} al {calc.get('end_date', '')}"
        percent_to_pay = float(calc.get("percent_to_pay", 0.0) or 0.0)

        currency_totals = {}
        grand_total_rd = 0.0
        selected_invoices_data = []

        for inv in invoices:
            if not inv.get("selected_for_calc", False):
                continue

            currency = inv.get("currency") or "RD$"
            rate = float(inv.get("exchange_rate", 1.0) or 1.0)
            
            # --- CORRECCIÓN CRÍTICA DE MONEDA ---
            # Problema: A veces 'itbis_original_currency' viene sucio con el valor en RD$
            # Solución: Si el valor original es casi igual al valor en RD$ pero la moneda NO es RD$,
            # asumimos que el valor original está mal y lo recalculamos.
            
            raw_itbis_orig = float(inv.get("itbis_original_currency", 0.0) or 0.0)
            raw_total_orig = float(inv.get("total_amount_original_currency", 0.0) or 0.0)
            
            itbis_rd = float(inv.get("itbis_rd") or inv.get("itbis", 0.0) or 0.0)
            total_rd = float(inv.get("total_amount_rd") or inv.get("total_amount", 0.0) or 0.0)
            
            # Validación de integridad para monedas extranjeras
            if currency not in ["RD$", "DOP"] and rate > 1.0:
                # Si el ITBIS original es sospechosamente cercano al ITBIS RD, recalcular
                if abs(raw_itbis_orig - itbis_rd) < 1.0 and itbis_rd > 0:
                    itbis_original = itbis_rd / rate
                elif raw_itbis_orig == 0:
                    itbis_original = itbis_rd / rate
                else:
                    itbis_original = raw_itbis_orig
                    
                # Misma validación para el total
                if abs(raw_total_orig - total_rd) < 1.0 and total_rd > 0:
                    total_original = total_rd / rate
                elif raw_total_orig == 0:
                    total_original = total_rd / rate
                else:
                    total_original = raw_total_orig
            else:
                # Si es RD$, los valores son directos
                itbis_original = itbis_rd
                total_original = total_rd
            
            # Cálculos finales usando los valores saneados
            valor_retencion_orig = itbis_original * 0.30 if inv.get("has_retention") else 0.0
            monto_a_pagar_orig = total_original * (percent_to_pay / 100.0)
            itbis_neto_orig = itbis_original - valor_retencion_orig
            total_impuestos_row_orig = itbis_neto_orig + monto_a_pagar_orig

            total_imp_rd = total_impuestos_row_orig * rate

            currency_totals.setdefault(currency, 0.0)
            currency_totals[currency] += total_impuestos_row_orig
            grand_total_rd += total_imp_rd

            selected_invoices_data.append({
                "fecha": format_date_for_report(inv.get("invoice_date")),
                "no_fact": str(inv.get("invoice_number", "")),
                "empresa": str(inv.get("third_party_name", "")),
                "currency": currency,
                "exchange_rate": rate,
                "total_orig": total_original,
                "total_rd": total_rd,
                "total_imp_orig": total_impuestos_row_orig,
                "total_imp_rd": total_imp_rd,
            })

        summary_data = {
            "percent_to_pay": percent_to_pay,
            "currency_totals": currency_totals,
            "grand_total_rd": grand_total_rd,
            "company_name": company_display,
        }

        return generate_advanced_retention_pdf(output_path, company_display, period_str, summary_data, selected_invoices_data)

    except Exception as e:
        logger.exception("Error wrapper tax pdf")
        return False, str(e)
    
        
def generate_profit_report_pdf(report_data, output_path):
    """
    Genera el Reporte de Utilidades (Profit & Loss Statement).
    
    Estructura de report_data:
    {
        "summary": {
            "total_income": float,
            "total_expense":  float,
            "additional_expenses": float,
            "net_profit":  float
        },
        "additional_expenses": [  # Lista de gastos adicionales
            {
                "date": datetime,
                "concept": str,
                "amount":  float,
                "category": str,
                "notes": str
            }
        ],
        "company_name": str,
        "period": str,  # "Enero 2025" o "Año 2025"
        "month": str,
        "year": str
    }
    """
    try:
        summary = report_data. get("summary", {})
        additional_expenses = report_data.get("additional_expenses", [])
        company_name = report_data.get("company_name", "Empresa")
        period = report_data.get("period", "")
        
        pdf = ModernPDF(
            orientation='P',
            company_name=company_name,
            report_title="Reporte de Utilidades",
            report_period=period,
        )
        pdf.add_page()

        # === KPI CARDS (2x2 Grid) ===
        full_width = pdf.w - 30
        card_gap = 8
        card_w = (full_width - card_gap) / 2
        card_h = 28
        
        y_start = pdf.get_y()
        
        # Fila 1: Ingresos y Gastos Facturados
        kpis_row1 = [
            {
                "label": "INGRESOS TOTALES",
                "value":  summary.get('total_income', 0.0),
                "color_accent":  COLORS['emerald_500'],
                "bg":  COLORS['emerald_50']
            },
            {
                "label": "GASTOS FACTURADOS",
                "value": summary.get('total_expense', 0.0),
                "color_accent": COLORS['red_500'],
                "bg": COLORS['red_50']
            }
        ]
        
        for i, kpi in enumerate(kpis_row1):
            x = 15 + (card_w + card_gap) * i
            
            pdf.set_fill_color_rgb(kpi['bg'])
            pdf.set_draw_color_rgb(COLORS['slate_200'])
            pdf.rounded_rect(x, y_start, card_w, card_h, 3, 'DF')
            
            pdf.set_fill_color_rgb(kpi['color_accent'])
            pdf.rounded_rect(x + 3, y_start + 3, 3, card_h - 6, 1.5, 'F')
            
            pdf.set_xy(x + 10, y_start + 6)
            pdf.set_font('Arial', 'B', 8)
            pdf.set_text_color_rgb(COLORS['slate_600'])
            pdf.cell(card_w - 15, 4, kpi['label'], 0, 1, 'L')
            
            pdf.set_xy(x + 10, y_start + 14)
            pdf.set_font('Arial', 'B', 14)
            pdf.set_text_color_rgb(kpi['color_accent'])
            pdf.cell(card_w - 15, 8, f"RD$ {kpi['value']: ,.2f}", 0, 1, 'L')

        pdf.set_y(y_start + card_h + card_gap)
        
        # Fila 2: Gastos Adicionales y Utilidad Neta
        y_row2 = pdf.get_y()
        
        kpis_row2 = [
            {
                "label": "GASTOS ADICIONALES",
                "value": summary.get('additional_expenses', 0.0),
                "color_accent": COLORS['red_600'],
                "bg": COLORS['red_50']
            },
            {
                "label":  "UTILIDAD NETA",
                "value": summary.get('net_profit', 0.0),
                "color_accent": COLORS['blue_600'],
                "bg":  COLORS['blue_50']
            }
        ]
        
        for i, kpi in enumerate(kpis_row2):
            x = 15 + (card_w + card_gap) * i
            
            pdf.set_fill_color_rgb(kpi['bg'])
            pdf.set_draw_color_rgb(COLORS['slate_200'])
            pdf.rounded_rect(x, y_row2, card_w, card_h, 3, 'DF')
            
            pdf.set_fill_color_rgb(kpi['color_accent'])
            pdf.rounded_rect(x + 3, y_row2 + 3, 3, card_h - 6, 1.5, 'F')
            
            pdf.set_xy(x + 10, y_row2 + 6)
            pdf.set_font('Arial', 'B', 8)
            pdf.set_text_color_rgb(COLORS['slate_600'])
            pdf.cell(card_w - 15, 4, kpi['label'], 0, 1, 'L')
            
            pdf.set_xy(x + 10, y_row2 + 14)
            pdf.set_font('Arial', 'B', 14)
            
            # Color especial para utilidad negativa
            if kpi['label'] == "UTILIDAD NETA" and kpi['value'] < 0:
                pdf.set_text_color_rgb(COLORS['red_600'])
            else:
                pdf.set_text_color_rgb(kpi['color_accent'])
            
            pdf.cell(card_w - 15, 8, f"RD$ {kpi['value']:,.2f}", 0, 1, 'L')

        pdf.set_y(y_row2 + card_h + 12)

        # === TABLA DE GASTOS ADICIONALES (ACUMULATIVOS) ===
        if additional_expenses:
            pdf. set_font('Arial', 'B', 11)
            pdf.set_text_color_rgb(COLORS['slate_800'])
            
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.set_fill_color_rgb(COLORS['red_500'])
            pdf.rounded_rect(x, y+1, 1, 4, 0.5, 'F')
            
            pdf.set_x(x + 3)
            pdf.cell(0, 6, "DETALLE DE GASTOS ADICIONALES (ACUMULATIVOS)", 0, 1, 'L')
            pdf.ln(2)
            
            # ✅ NUEVO: Mostrar conceptos acumulativos
            # additional_expenses ahora es una lista de conceptos anuales
            is_annual_format = False
            if additional_expenses and isinstance(additional_expenses[0], dict):
                if "monthly_values" in additional_expenses[0]: 
                    is_annual_format = True
            
            if is_annual_format:
                # === FORMATO NUEVO: Conceptos Anuales ===
                headers = ["Concepto", "Categoría", "Valor Mes", "Acum. Año", "Variación"]
                col_widths_pct = [30, 18, 17, 17, 18]
                col_widths = [(pct/100) * full_width for pct in col_widths_pct]
                
                pdf.set_font('Arial', 'B', 8)
                pdf.set_text_color_rgb(COLORS['slate_500'])
                pdf.set_fill_color_rgb(COLORS['slate_50'])
                pdf.set_draw_color_rgb(COLORS['slate_200'])
                
                pdf.rect(15, pdf.get_y(), full_width, 8, 'F')
                
                start_x = 15
                for i, h_text in enumerate(headers):
                    align = 'R' if i >= 2 else 'L'
                    pdf.set_xy(start_x, pdf.get_y())
                    pdf. cell(col_widths[i], 8, h_text, 0, 0, align)
                    start_x += col_widths[i]
                pdf.ln(8)
                
                # Rows
                pdf.set_font('Arial', '', 8)
                pdf.set_text_color_rgb(COLORS['slate_600'])
                
                month_str = report_data.get("month_str", "12")  # Necesitas pasarlo desde profit_summary_window
                
                total_mes = 0.0
                total_año = 0.0
                
                for concept in additional_expenses:
                    if pdf.get_y() > 270: 
                        pdf.add_page()
                        # Repetir header
                        pdf.set_font('Arial', 'B', 8)
                        pdf.set_text_color_rgb(COLORS['slate_500'])
                        pdf.set_fill_color_rgb(COLORS['slate_50'])
                        pdf.rect(15, pdf.get_y(), full_width, 8, 'F')
                        start_x = 15
                        for i, h_text in enumerate(headers):
                            align = 'R' if i >= 2 else 'L'
                            pdf.set_xy(start_x, pdf.get_y())
                            pdf.cell(col_widths[i], 8, h_text, 0, 0, align)
                            start_x += col_widths[i]
                        pdf.ln(8)
                        pdf.set_font('Arial', '', 8)
                        pdf. set_text_color_rgb(COLORS['slate_600'])

                    concept_name = concept.get("concept", "")
                    category = concept.get("category", "")
                    monthly_values = concept.get("monthly_values", {})
                    
                    # Valor del mes
                    value_month = float(monthly_values.get(month_str, 0.0) or 0.0)
                    
                    # Si no existe, buscar anterior
                    if value_month == 0.0:
                        month_int = int(month_str)
                        for m in range(month_int - 1, 0, -1):
                            m_str = f"{m:02d}"
                            if m_str in monthly_values:
                                value_month = float(monthly_values[m_str] or 0.0)
                                break
                    
                    # Acumulado año (último valor disponible o diciembre)
                    value_year = value_month
                    for m in range(12, int(month_str), -1):
                        m_str = f"{m:02d}"
                        if m_str in monthly_values:
                            value_year = float(monthly_values[m_str] or 0.0)
                            break
                    
                    # Calcular variación (mes anterior vs mes actual)
                    month_int = int(month_str)
                    value_prev = 0.0
                    if month_int > 1:
                        prev_month_str = f"{month_int - 1:02d}"
                        if prev_month_str in monthly_values: 
                            value_prev = float(monthly_values[prev_month_str] or 0.0)
                    
                    variation = value_month - value_prev
                    variation_str = f"+{variation: ,.2f}" if variation >= 0 else f"{variation:,.2f}"
                    
                    total_mes += value_month
                    total_año += value_year
                    
                    row_data = [
                        concept_name[: 35],
                        category[: 20],
                        f"{value_month:,.2f}",
                        f"{value_year:,.2f}",
                        variation_str
                    ]
                    
                    start_x = 15
                    for i, cell_val in enumerate(row_data):
                        align = 'R' if i >= 2 else 'L'
                        
                        if i == 3:  # Acumulado año
                            pdf. set_font('Arial', 'B', 8)
                            pdf.set_text_color_rgb(COLORS['emerald_600'])
                        elif i == 4:  # Variación
                            pdf. set_font('Arial', 'B', 8)
                            color = COLORS['emerald_600'] if variation >= 0 else COLORS['red_600']
                            pdf.set_text_color_rgb(color)
                        else:
                            pdf.set_font('Arial', '', 8)
                            pdf.set_text_color_rgb(COLORS['slate_600'])
                        
                        pdf. set_xy(start_x, pdf.get_y())
                        pdf.cell(col_widths[i], 7, cell_val, 'B', 0, align)
                        start_x += col_widths[i]
                    pdf.ln(7)
                
                # Total row
                pdf.ln(2)
                pdf.set_draw_color_rgb(COLORS['slate_800'])
                pdf.line(15, pdf.get_y(), 15 + full_width, pdf.get_y())
                pdf.ln(3)
                
                start_x = 15
                for i in range(len(headers)):
                    pdf.set_xy(start_x, pdf.get_y())
                    
                    if i == 0:
                        pdf.set_font('Arial', 'B', 9)
                        pdf.set_text_color_rgb(COLORS['slate_800'])
                        pdf.cell(col_widths[i], 7, "TOTAL:", 0, 0, 'L')
                    elif i == 2:
                        pdf.set_font('Arial', 'B', 10)
                        pdf.set_text_color_rgb(COLORS['red_600'])
                        pdf. cell(col_widths[i], 7, f"{total_mes:,.2f}", 0, 0, 'R')
                    elif i == 3:
                        pdf.set_font('Arial', 'B', 10)
                        pdf.set_text_color_rgb(COLORS['emerald_600'])
                        pdf.cell(col_widths[i], 7, f"{total_año:,.2f}", 0, 0, 'R')
                    else:
                        pdf.cell(col_widths[i], 7, "", 0, 0, 'L')
                    
                    start_x += col_widths[i]
                
            else:
                # === FORMATO ANTIGUO: Compatibilidad ===
                # (Mantener código anterior para datos viejos)
                pass
            
            pdf.ln(10)

        # === RESUMEN FINAL (Estilo Extracto) ===
        if pdf.get_y() > 230:
            pdf.add_page()
        
        card_final_h = 50
        card_final_w = full_width
        x_final = 15
        y_final = pdf.get_y()
        
        pdf.set_fill_color_rgb(COLORS['slate_900'])
        pdf.rounded_rect(x_final, y_final, card_final_w, card_final_h, 4, 'F')
        
        # Columna Izquierda
        pdf.set_xy(x_final + 15, y_final + 10)
        pdf.set_font('Arial', 'B', 9)
        pdf.set_text_color_rgb(COLORS['slate_400'])
        pdf.cell(80, 5, "ESTADO DE RESULTADOS", 0, 1, 'L')
        
        pdf.set_x(x_final + 15)
        pdf.set_font('Arial', '', 8)
        pdf.cell(80, 5, f"Período: {period}", 0, 1, 'L')
        
        pdf.set_x(x_final + 15)
        pdf.set_font('Arial', '', 7)
        pdf.set_text_color_rgb(COLORS['slate_500'])
        pdf.cell(80, 5, f"Empresa: {company_name}", 0, 1, 'L')
        
        # Línea divisoria
        pdf.set_draw_color_rgb(COLORS['slate_700'])
        pdf.line(x_final + (card_final_w/2), y_final + 8, 
                 x_final + (card_final_w/2), y_final + card_final_h - 8)
        
        # Columna Derecha:  Utilidad Neta
        net_profit = summary.get('net_profit', 0.0)
        
        pdf.set_xy(x_final + (card_final_w/2) + 15, y_final + 10)
        pdf.set_font('Arial', 'B', 9)
        
        if net_profit >= 0:
            pdf.set_text_color_rgb(COLORS['emerald_500'])
            status = "UTILIDAD POSITIVA"
        else:
            pdf.set_text_color_rgb(COLORS['red_500'])
            status = "PÉRDIDA"
        
        pdf.cell(80, 5, status, 0, 1, 'L')
        
        pdf.set_xy(x_final + (card_final_w/2) + 15, y_final + 18)
        pdf.set_font('Arial', 'B', 20)
        pdf.set_text_color_rgb(COLORS['white'])
        pdf.cell(80, 10, f"RD$ {net_profit:,.2f}", 0, 1, 'L')
        
        pdf.set_xy(x_final + (card_final_w/2) + 15, y_final + 32)
        pdf.set_font('Arial', '', 7)
        pdf.set_text_color_rgb(COLORS['slate_400'])
        
        # Calcular porcentaje de margen
        total_income = summary.get('total_income', 0.0)
        margin_pct = (net_profit / total_income * 100) if total_income > 0 else 0
        pdf.cell(80, 4, f"Margen: {margin_pct:.1f}%", 0, 1, 'L')

        pdf.output(output_path)
        return True, "Reporte de Utilidades generado exitosamente."

    except Exception as e: 
        logger.exception("Error generando PDF de utilidades")
        return False, f"Error generando PDF: {e}"