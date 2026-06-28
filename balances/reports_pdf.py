"""Pure-ReportLab PDF reports with Arabic (RTL) support."""
import sys, hashlib
if sys.version_info < (3, 9):
    _real_md5 = hashlib.md5
    def _md5_compat(data=b"", *args, **kwargs):
        kwargs.pop("usedforsecurity", None)
        return _real_md5(data, *args, **kwargs)
    hashlib.md5 = _md5_compat

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import ParagraphStyle
import arabic_reshaper
from bidi.algorithm import get_display

# ---- font registration (do this ONCE, at import) -------------------------
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
pdfmetrics.registerFont(TTFont("Amiri", os.path.join(FONT_DIR, "Amiri-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Amiri-Bold", os.path.join(FONT_DIR, "Amiri-Bold.ttf")))
pdfmetrics.registerFontFamily("Amiri", normal="Amiri", bold="Amiri-Bold")


def ar(text):
    """Reshape + reorder Arabic so it connects and reads right-to-left.
    Safe to call on plain numbers / Latin too."""
    if text is None:
        return ""
    return get_display(arabic_reshaper.reshape(str(text)))


# ---- shared colors -------------------------------------------------------
GRID = colors.HexColor("#d0d0d0")
ZEBRA = colors.HexColor("#f4f7fb")
RANK1 = colors.HexColor("#fff3cd")
RANK2 = colors.HexColor("#e9ecef")
RANK3 = colors.HexColor("#f5e6d3")


def _doc(buf_or_path, brand):
    return SimpleDocTemplate(
        buf_or_path, pagesize=A4,
        topMargin=1.2 * cm, bottomMargin=1.2 * cm,
        leftMargin=1.2 * cm, rightMargin=1.2 * cm,
        title="report",
    )


def _header(title, date_from, date_to, brand):
    h = ParagraphStyle("h", fontName="Amiri-Bold", fontSize=20,
                       textColor=brand, alignment=TA_RIGHT, leading=24)
    r = ParagraphStyle("r", fontName="Amiri", fontSize=12,
                       textColor=colors.HexColor("#555555"),
                       alignment=TA_RIGHT, leading=16)
    rng = ar(f"من {date_from} إلى {date_to}")
    return [Paragraph(ar(title), h), Spacer(1, 4), Paragraph(rng, r), Spacer(1, 10)]


def _rank_bg(style, n_rows):
    """Apply rank-1/2/3 row backgrounds + zebra for the rest.
    Row 0 is the header; data rows start at index 1."""
    rank_colors = {1: RANK1, 2: RANK2, 3: RANK3}
    for i in range(1, n_rows + 1):           # data rows
        if i in rank_colors:
            style.add("BACKGROUND", (0, i), (-1, i), rank_colors[i])
        elif i % 2 == 0:
            style.add("BACKGROUND", (0, i), (-1, i), ZEBRA)


# ==========================================================================
# CUSTOMERS REPORT
# ==========================================================================
def build_customers_pdf(buf, rows, date_from, date_to,
                        total_vehicles, total_revenue):
    brand = colors.HexColor("#1f6feb")
    doc = _doc(buf, brand)
    elements = _header("تقرير أعلى العملاء", date_from, date_to, brand)

    name_style = ParagraphStyle("name", fontName="Amiri", fontSize=12,
                                alignment=TA_RIGHT, leading=15)

    # RTL: columns laid out right-to-left -> [revenue, vehicles, name, #]
    header = [ar("الإيرادات"), ar("عدد المركبات"), ar("العميل"), ar("#")]
    data = [header]
    for i, rrow in enumerate(rows, start=1):
        data.append([
            f"{float(rrow['revenue']):,.2f}",
            str(rrow["vehicles"]),
            Paragraph(ar(rrow["name"]), name_style),
            str(i),
        ])
    data.append([f"{float(total_revenue):,.2f}", str(total_vehicles),
                 "", ar("الإجمالي")])

    # column widths sum to usable width (A4 minus 2.4cm margins ~= 18.6cm)
    col_w = [4.6 * cm, 3.6 * cm, None, 1.6 * cm]  # name col flexes
    usable = A4[0] - 2.4 * cm
    col_w[2] = usable - (4.6 + 3.6 + 1.6) * cm

    t = Table(data, colWidths=col_w, repeatRows=1)
    st = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Amiri"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("GRID", (0, 0), (-1, -1), 0.75, GRID),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        # header band
        ("BACKGROUND", (0, 0), (-1, 0), brand),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Amiri-Bold"),
        # the name column reads right-aligned
        ("ALIGN", (2, 1), (2, -2), "RIGHT"),
        # footer band
        ("BACKGROUND", (0, -1), (-1, -1), brand),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Amiri-Bold"),
        ("SPAN", (2, -1), (3, -1)),  # "الإجمالي" spans name + # cells
    ])
    _rank_bg(st, len(rows))
    t.setStyle(st)
    elements.append(t)
    doc.build(elements)


# ==========================================================================
# DRIVERS REPORT
# ==========================================================================
def build_drivers_pdf(buf, rows, date_from, date_to, total_vehicles):
    brand = colors.HexColor("#198754")
    doc = _doc(buf, brand)
    elements = _header("تقرير أداء السائقين", date_from, date_to, brand)

    name_style = ParagraphStyle("name", fontName="Amiri", fontSize=13,
                                alignment=TA_RIGHT, leading=16)

    header = [ar("عدد المركبات المنقولة"), ar("السائق"), ar("#")]
    data = [header]
    for i, rrow in enumerate(rows, start=1):
        data.append([
            str(rrow["vehicles"]),
            Paragraph(ar(rrow["name"]), name_style),
            str(i),
        ])
    data.append([str(total_vehicles), "", ar("الإجمالي")])

    usable = A4[0] - 2.4 * cm
    col_w = [5.5 * cm, None, 1.8 * cm]
    col_w[1] = usable - (5.5 + 1.8) * cm

    t = Table(data, colWidths=col_w, repeatRows=1)
    st = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Amiri"),
        ("FONTSIZE", (0, 0), (-1, -1), 13),
        ("GRID", (0, 0), (-1, -1), 0.75, GRID),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("BACKGROUND", (0, 0), (-1, 0), brand),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Amiri-Bold"),
        ("ALIGN", (1, 1), (1, -2), "RIGHT"),
        ("BACKGROUND", (0, -1), (-1, -1), brand),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Amiri-Bold"),
        ("SPAN", (1, -1), (2, -1)),
    ])
    _rank_bg(st, len(rows))
    t.setStyle(st)
    elements.append(t)
    doc.build(elements)


# ---- quick self-test -----------------------------------------------------
if __name__ == "__main__":
    cust_rows = [
        {"name": "بوندد القسطل - المركزية", "vehicles": 272, "revenue": 9546},
        {"name": "بوندد حرة الزرقاء - المركزية", "vehicles": 170, "revenue": 5491},
        {"name": "الشركة المركزية للوكالات التجارية", "vehicles": 23, "revenue": 990},
        {"name": "شركة ياماها المعرض", "vehicles": 18, "revenue": 515},
        {"name": "Markazia Marketing", "vehicles": 8, "revenue": 370},
    ]
    build_customers_pdf("/tmp/out_customers.pdf", cust_rows,
                        "2026-05-13", "2026-06-12",
                        sum(r["vehicles"] for r in cust_rows),
                        sum(r["revenue"] for r in cust_rows))

    drv_rows = [
        {"name": "أحمد المصري", "vehicles": 120},
        {"name": "خالد عبدالله", "vehicles": 98},
        {"name": "محمد سالم", "vehicles": 77},
        {"name": "John Driver", "vehicles": 40},
    ]
    build_drivers_pdf("/tmp/out_drivers.pdf", drv_rows,
                      "2026-05-13", "2026-06-12",
                      sum(r["vehicles"] for r in drv_rows))
    print("built")
