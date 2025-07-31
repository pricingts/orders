from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import PyPDF2
from reportlab.platypus import Table, TableStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from datetime import datetime
import os
from textwrap import wrap
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from ui.helpers import prepare_venta_data

# ----------------------------------------------------------------------
# Utilidad para “wrappear” texto
# ----------------------------------------------------------------------
def wrap_text(text, max_chars):
    lines = []
    words = text.split()
    line = ""
    for word in words:
        if len(line + " " + word) <= max_chars:
            line = f"{line} {word}".strip()
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines

def draw_wrapped_string(c, x, y, text, max_chars, line_height=7):
    lines = wrap_text(text, max_chars)
    for i, line in enumerate(lines):
        c.drawString(x, y - i * line_height, line)

# ----------------------------------------------------------------------
# Registro de fuentes (sobrescribe las advertencias originales)
# ----------------------------------------------------------------------
FONT_REGULAR = "OpenSauce"
FONT_BOLD    = "OpenSauceBold"

def _register_fonts():
    font_path = "resources/fonts/OpenSauceSans-Regular.ttf"
    font_bold = "resources/fonts/OpenSauceSans-Bold.ttf"
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont(FONT_REGULAR, font_path))
    if os.path.exists(font_bold):
        pdfmetrics.registerFont(TTFont(FONT_BOLD,   font_bold))

_register_fonts()

# ----------------------------------------------------------------------
# Capa de datos (overlay)
# ----------------------------------------------------------------------

def create_overlay(data: dict, overlay_path: str, surcharge_key: str = "sales_surcharges", page: int = 1, apply_markup: bool = False):
    c = canvas.Canvas(overlay_path, pagesize=letter)

    surcharges = data.get(surcharge_key, [])
    is_last_page = False

    if page == 1:
        current_date = datetime.today().strftime("%d/%m/%Y")

        c.setFont(FONT_REGULAR, 6)
        c.drawString(442, 590, data.get("no_solicitud", "").upper()) 

        c.setFont(FONT_BOLD, 7)
        c.drawString(500, 669, current_date)

        c.setFont(FONT_REGULAR, 7)
        c.drawString(115, 583, data.get("client", "").upper())
        c.drawString(170, 569, data.get("customer_account", "").upper())
        c.drawString(95, 555, data.get("customer_nit", "").upper())
        c.drawString(105, 540, data.get("customer_email", "").upper())

        address_text = data.get("customer_address", "").upper()

        max_chars    = 30   
        line_height  = 11       
        x_address    = 125
        y_address_start = 527

        c.setFont(FONT_REGULAR, 7) 

        lines = []
        for paragraph in address_text.split("\n"):
            wrapped_lines = wrap(paragraph, max_chars)
            lines.extend(wrapped_lines if wrapped_lines else [""])

        for i, line in enumerate(lines):
            y = y_address_start - i * line_height
            c.drawString(x_address, y, line)

        # ----------------------- datos transporte / referencia --------------------
        c.setFont(FONT_REGULAR, 6)

        draw_wrapped_string(c, 282, 590, data.get("bl_awb", "").upper(), max_chars=20)
        draw_wrapped_string(c, 442, 510, data.get("pod_aod", "").upper(), max_chars=20)
        draw_wrapped_string(c, 282, 510, data.get("pol_aol", "").upper(), max_chars=20)
        draw_wrapped_string(c, 282, 550, data.get("shipper", "").upper(), max_chars=20)
        draw_wrapped_string(c, 442, 550, data.get("consignee", "").upper(), max_chars=20)

        ref_text     = data.get("reference", "").upper() 
        max_chars    = 20            # ~ ancho de unos 120 pt a font-size 7 (ajústalo)
        line_height  = 11           # puntos de separación vertical
        x_ref        = 282
        y_ref_start  = 470         # coordenada de la 1.ª línea

        c.setFont(FONT_REGULAR, 6)

        lines = []
        for paragraph in ref_text.split("\n"):
            wrapped_lines = wrap(paragraph, max_chars)
            lines.extend(wrapped_lines if wrapped_lines else [""])

        for i, line in enumerate(lines):
            y = y_ref_start - i * line_height
            c.drawString(x_ref, y, line)

        # ────────────────── Nombres de contenedor uno debajo de otro ──────────────────
        c.setFont(FONT_REGULAR, 6)

        # Configuración de columnas
        x_start     = 75        # Columna izquierda
        x_gap       = 115       # Distancia horizontal entre columnas
        y_start     = 455       # Coordenada Y inicial
        line_height = 11        # Separación vertical
        max_rows    = 5         # Máximo de filas antes de pasar a la siguiente columna

        cargo_type = (data.get("cargo_type") or "").strip().lower()
        container_details = data.get("container_details") or {}

        if cargo_type == "carga suelta" or not container_details:
            unidad = str(data.get("unidad_medida", "")).upper()
            cantidad = data.get("cantidad_suelta", "")
            c.drawString(x_start, y_start, f"{cantidad} {unidad}")
        else:
            row_count = 0
            col_count = 0
            for ctype, details in container_details.items():
                cont_type = ctype.upper()
                for name in details.get("names", []):
                    # Calcular posición en función de la columna
                    x_pos = x_start + (col_count * x_gap)
                    y_pos = y_start - (row_count * line_height)
                    
                    line_text = f"{name.upper()} - {cont_type}"
                    c.drawString(x_pos, y_pos, line_text)
                    
                    row_count += 1
                    if row_count >= max_rows:
                        row_count = 0
                        col_count += 1  # Avanzar a la siguiente columna

        if page == 1:
            surcharges_to_draw = surcharges[:10]
        elif page == 2:
            surcharges_to_draw = surcharges[10:]
        else:
            surcharges_to_draw = []

        table_data = []

        for surcharge in surcharges_to_draw:
            concept   = surcharge.get("concept", "").upper()
            quantity  = surcharge.get("quantity", 0)
            rate      = surcharge.get("rate", 0)
            total     = surcharge.get("total", rate * quantity)
            currency  = surcharge.get("currency", "")

            table_data.append([
                concept,               # Concepto
                str(quantity),         # Cantidad
                f"${rate:,.2f}",       # Tarifa / Rate
                f"${total:,.2f}",      # Total
                currency,              # Moneda
            ])

        # ──────────────────────────────────────────────────────────────────────────
        # Sólo procedemos si HAY datos
        # ──────────────────────────────────────────────────────────────────────────
        if table_data:
            col_widths = [180, 150, 20, 130, 50]
            table = Table(table_data, colWidths=col_widths)

            table.setStyle(TableStyle([
                ("FONTNAME",  (0, 0), (-1, -1), FONT_REGULAR),
                ("FONTSIZE",  (0, 0), (-1, -1), 6),
                ("ALIGN",     (0, 0), (-1, -1), "CENTER"),
                ("VALIGN",    (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",    (0, 0), (-1, -1), 0.3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0.3),
                ("LEFTPADDING",   (0, 0), (-1, -1), 1),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 1),
            ]))

            x, y = 10, 358
            table.wrapOn(c, 0, 0)
            table.drawOn(c, x, y - table._height)

        is_last_page = (len(surcharges) <= 10)

    elif page == 2:
        # Dibujar solo recargos de la página 2
        surcharges_to_draw = surcharges[10:]
        table_data = []
        for surcharge in surcharges_to_draw:
            concept   = surcharge.get("concept", "").upper()
            quantity  = surcharge.get("quantity", 0)
            rate      = surcharge.get("rate", 0)
            total     = surcharge.get("total", rate * quantity)
            currency  = surcharge.get("currency", "")
            table_data.append([
                concept, str(quantity), f"${rate:,.2f}", f"${total:,.2f}", currency,
            ])

        if table_data:
            col_widths = [180, 150, 20, 130, 50]
            table = Table(table_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ("FONTNAME",  (0, 0), (-1, -1), FONT_REGULAR),
                ("FONTSIZE",  (0, 0), (-1, -1), 6),
                ("ALIGN",     (0, 0), (-1, -1), "CENTER"),
                ("VALIGN",    (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",    (0, 0), (-1, -1), 0.3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0.3),
                ("LEFTPADDING",   (0, 0), (-1, -1), 1),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 1),
            ]))
            x, y = 10, 560
            table.wrapOn(c, 0, 0)
            table.drawOn(c, x, y - table._height)

        # Página 2 siempre es la última
        is_last_page = True

    if is_last_page:
        totales = defaultdict(Decimal)
        for s in surcharges:
            currency = s.get("currency", "").upper()
            base_total = Decimal(s.get("total", 0))
            if apply_markup:
                base_total *= Decimal("1.04")  # Aplica 4% si es costos
            total = base_total.quantize(Decimal("0.01"), ROUND_HALF_UP)
            totales[currency] += total

        x_label, x_value, y_start, line_height = 450, 510, 210, 13
        c.setFont(FONT_BOLD, 8)
        for i, (curr, total) in enumerate(totales.items()):
            y_pos = y_start - i * line_height
            c.drawString(x_label, y_pos, f"TOTAL {curr}")
            formatted = f"${total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            c.drawString(x_value, y_pos, formatted)

        comments = data.get("comentarios", "").upper()
        x_comments, y_comments, max_chars, comments_height = 60, 120, 110, 11
        c.setFont(FONT_REGULAR, 6)
        for i, line in enumerate(wrap(comments, max_chars)):
            c.drawString(x_comments, y_comments - i * comments_height, line)

    c.save()

# ----------------------------------------------------------------------
# Combinar plantilla + overlay
# ----------------------------------------------------------------------

def merge_pdfs(template_path, overlay_path, output_path):
    template_pdf = PyPDF2.PdfReader(template_path)
    overlay_pdf = PyPDF2.PdfReader(overlay_path)
    writer = PyPDF2.PdfWriter()

    for idx, template_page in enumerate(template_pdf.pages):
        if idx < len(overlay_pdf.pages):
            template_page.merge_page(overlay_pdf.pages[idx])
        writer.add_page(template_page)

    with open(output_path, "wb") as f_out:
        writer.write(f_out)

# ----------------------------------------------------------------------
# Función pública que genera el PDF
# ----------------------------------------------------------------------
def generate_pdf(
    quotation_data: dict,
    template_path="resources/templates/PRE ORDEN COSTOS 1.pdf",
    output_path="resources/output/pre_orden_ventas.pdf",
    overlay_path="resources/templates/overlay.pdf",
):
    create_overlay(quotation_data, overlay_path)
    merge_pdfs(template_path, overlay_path, output_path)
    return output_path

def generate_archives(venta_info: dict, variant: str = "ventas"):
    data = prepare_venta_data(venta_info)

    surcharge_key = "sales_surcharges" if variant == "ventas" else "cost_surcharges"
    num_surcharges = len(data.get(surcharge_key, []))
    template_version = "short" if num_surcharges <= 10 else "long"

    config = {
        "ventas": {
            "surcharge_key": "sales_surcharges",
            "template": {
                "short": "resources/templates/ORDER1.pdf",
                "long": "resources/templates/ORDER2.pdf",
            },
            "output": "resources/output/pre_orden_ventas.pdf",
        },
        "costos": {
            "surcharge_key": "cost_surcharges",
            "template": {
                "short": "resources/templates/PRE_ORDER1.pdf",
                "long": "resources/templates/PRE_ORDER2.pdf",
            },
            "output": "resources/output/pre_orden_costos.pdf",
        },
    }

    if variant not in config:
        raise ValueError(f"Variant desconocida: {variant}")

    cfg = config[variant]
    selected_template = cfg["template"][template_version]

    pages_needed = 1 if template_version == "short" else 2
    overlay_paths = []

    for page in range(1, pages_needed + 1):
        overlay_path = f"resources/temp/overlay_{variant}_page{page}.pdf"
        os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
        create_overlay(data, overlay_path, cfg["surcharge_key"], page, apply_markup=(variant == "costos"))
        overlay_paths.append(overlay_path)

    # Combina todas las páginas
    combined_overlay_path = f"resources/temp/combined_overlay_{variant}.pdf"
    overlay_writer = PyPDF2.PdfWriter()
    for path in overlay_paths:
        overlay_pdf = PyPDF2.PdfReader(path)
        overlay_writer.add_page(overlay_pdf.pages[0])
    with open(combined_overlay_path, "wb") as f_out:
        overlay_writer.write(f_out)

    merge_pdfs(selected_template, combined_overlay_path, cfg["output"])

    return cfg["output"]
