"""
ReportLab PDF reports for the driver balance page (Arabic / RTL).
 
Replaces the old openpyxl + LibreOffice pipeline.
Builders take plain Python data (lists of dicts) so they are easy to test
and decoupled from Django.
 
Dependencies:  pip install reportlab arabic-reshaper python-bidi
Fonts (with Arabic glyphs) live in a `fonts/` folder beside this file:
    Amiri-Regular.ttf, Amiri-Bold.ttf
"""
# --- Python 3.8 compatibility: hashlib.md5 has no usedforsecurity kwarg ----
import sys, hashlib
if sys.version_info < (3, 9):
    _real_md5 = hashlib.md5
    def _md5_compat(data=b"", *args, **kwargs):
        kwargs.pop("usedforsecurity", None)
        return _real_md5(data, *args, **kwargs)
    hashlib.md5 = _md5_compat
# ---------------------------------------------------------------------------
 
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import ParagraphStyle
import arabic_reshaper
from bidi.algorithm import get_display
 
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
pdfmetrics.registerFont(TTFont("Amiri", os.path.join(FONT_DIR, "Amiri-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Amiri-Bold", os.path.join(FONT_DIR, "Amiri-Bold.ttf")))
pdfmetrics.registerFontFamily("Amiri", normal="Amiri", bold="Amiri-Bold")
 
 
def ar(text):
    """Reshape + reorder Arabic so it connects and reads RTL. Safe on numbers/Latin."""
    if text is None:
        return ""
    return get_display(arabic_reshaper.reshape(str(text)))
 
 
GRID = colors.HexColor("#d0d0d0")
ZEBRA = colors.HexColor("#f4f7fb")
 
 
def _doc(buf):
    return SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=1.2 * cm, bottomMargin=1.2 * cm,
        leftMargin=1.2 * cm, rightMargin=1.2 * cm, title="report",
    )
 
 
def _header(title, date_from, date_to, brand):
    h = ParagraphStyle("h", fontName="Amiri-Bold", fontSize=20,
                       textColor=brand, alignment=TA_RIGHT, leading=24)
    r = ParagraphStyle("r", fontName="Amiri", fontSize=12,
                       textColor=colors.HexColor("#555555"),
                       alignment=TA_RIGHT, leading=16)
    return [Paragraph(ar(title), h), Spacer(1, 4),
            Paragraph(ar(f"من {date_from} إلى {date_to}"), r), Spacer(1, 10)]
 
 
def _base_style(brand, font_size=12):
    return [
        ("FONTNAME", (0, 0), (-1, -1), "Amiri"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("GRID", (0, 0), (-1, -1), 0.75, GRID),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 0), (-1, 0), brand),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Amiri-Bold"),
    ]
 
 
def _zebra(style, n_data_rows, last_is_total=False):
    end = n_data_rows if not last_is_total else n_data_rows - 1
    for i in range(1, end + 1):
        if i % 2 == 0:
            style.add("BACKGROUND", (0, i), (-1, i), ZEBRA)
 
 
def _fmt_dt(dt):
    return dt.strftime("%Y-%m-%d %H:%M") if hasattr(dt, "strftime") else str(dt)


def _fmt_date(d):
    """Date only, no 00:00 time component."""
    return d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)


def _p(text, align="CENTER", size=11):
    """Wrapping cell: long values break onto new lines instead of overflowing.
    wordWrap='CJK' also breaks long unspaced tokens (e.g. plate/VIN numbers)."""
    style = ParagraphStyle(
        "cell", fontName="Amiri", fontSize=size, leading=size + 3,
        alignment=TA_RIGHT if align == "RIGHT" else TA_CENTER, wordWrap="CJK",
    )
    return Paragraph(ar(text), style)
 
 
# ==========================================================================
# 1) ACCOUNT STATEMENT  (replaces the Excel + LibreOffice export)
# ==========================================================================
def build_account_statement_pdf(buf, driver_name, date_from, date_to,
                                entries, total_invoiced, total_treasury,
                                required_amount):
    brand = colors.HexColor("#1f6feb")
    doc = _doc(buf)
    el = _header(f"كشف حركة حساب السائق / {driver_name}", date_from, date_to, brand)
 
    header = [ar("التاريخ"), ar("المبلغ"), ar("رقم الفاتورة"), ar("الحركة")]
    data = [header]
    pay_rows = []
    for e in entries:
        if e["account"] == "سداد":
            pay_rows.append(len(data))
        data.append([_fmt_date(e["created_at"]),
                     f"{float(e['amount'] or 0):,.2f}",
                     str(e["number"] or ""), ar(e["account"])])
 
    usable = A4[0] - 2.4 * cm
    col_w = [5.0 * cm, 4.0 * cm, 4.0 * cm, None]
    col_w[3] = usable - (5.0 + 4.0 + 4.0) * cm
 
    t = Table(data, colWidths=col_w, repeatRows=1)
    st = TableStyle(_base_style(brand))
    _zebra(st, len(entries))
    for r in pay_rows:                       # highlight "سداد" rows in yellow
        st.add("BACKGROUND", (0, r), (-1, r), colors.HexColor("#fff3cd"))
    t.setStyle(st)
    el.append(t)
    el.append(Spacer(1, 12))
 
    # totals block
    tot = [
        [f"{float(total_invoiced):,.2f}", ar("إجمالي الفواتير")],
        [f"{float(total_treasury):,.2f}", ar("إجمالي المسدد")],
        [f"{float(required_amount):,.2f}", ar("المتبقي")],
    ]
    tt = Table(tot, colWidths=[5.0 * cm, 6.0 * cm], hAlign="RIGHT")
    tt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Amiri-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("GRID", (0, 0), (-1, -1), 0.75, GRID),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#eef3fb")),
        ("BACKGROUND", (0, 2), (-1, 2), brand),
        ("TEXTCOLOR", (0, 2), (-1, 2), colors.white),
    ]))
    el.append(tt)
    doc.build(el)
 
 
# ==========================================================================
# 2) TRIPS REPORT  (number of trips = rows)
# ==========================================================================
def build_trips_pdf(buf, driver_name, date_from, date_to, trips, total_cost):
    brand = colors.HexColor("#198754")
    doc = _doc(buf)
    el = _header(f"تقرير رحلات السائق / {driver_name}", date_from, date_to, brand)
 
    name_style = ParagraphStyle("n", fontName="Amiri", fontSize=11,
                                alignment=TA_RIGHT, leading=14)
    header = [ar("التكلفة"), ar("عدد المركبات"), ar("إلى"), ar("من"),
              ar("العميل"), ar("التاريخ"), ar("#")]
    data = [header]
    for i, tr in enumerate(trips, start=1):
        data.append([
            f"{float(tr['cost'] or 0):,.2f}",
            str(tr["vehicles"]),
            _p(tr["to_location"] or ""),
            _p(tr["from_location"] or ""),
            _p(tr["customer"] or "", align="RIGHT"),
            _p(_fmt_date(tr["date"])),
            str(i),
        ])
    data.append([f"{float(total_cost or 0):,.2f}",
                 str(sum(t["vehicles"] for t in trips)),
                 "", "", "", ar(f"عدد الرحلات: {len(trips)}"), ar("الإجمالي")])
 
    usable = A4[0] - 2.4 * cm
    fixed = (2.4 + 2.2 + 2.4 + 1.0) * cm    # cost, vehicles, date, #
    col_w = [2.4 * cm, 2.2 * cm, None, None, None, 2.4 * cm, 1.0 * cm]
    flex = (usable - fixed) / 3.0
    col_w[2] = col_w[3] = col_w[4] = flex
 
    t = Table(data, colWidths=col_w, repeatRows=1)
    st = TableStyle(_base_style(brand, font_size=11))
    _zebra(st, len(trips))
    st.add("BACKGROUND", (0, -1), (-1, -1), brand)
    st.add("TEXTCOLOR", (0, -1), (-1, -1), colors.white)
    st.add("FONTNAME", (0, -1), (-1, -1), "Amiri-Bold")
    st.add("SPAN", (2, -1), (4, -1))
    t.setStyle(st)
    el.append(t)
    doc.build(el)
 
 
# ==========================================================================
# 3) VEHICLES TRANSPORTED REPORT
# ==========================================================================
def build_vehicles_pdf(buf, driver_name, date_from, date_to, vehicles):
    brand = colors.HexColor("#6f42c1")
    doc = _doc(buf)
    el = _header(f"تقرير المركبات المنقولة / {driver_name}", date_from, date_to, brand)
 
    name_style = ParagraphStyle("n", fontName="Amiri", fontSize=11,
                                alignment=TA_RIGHT, leading=14)
    header = [ar("اللون"), ar("رقم اللوحة"), ar("الماركة"), ar("النوع"),
              ar("العميل"), ar("التاريخ"), ar("#")]
    data = [header]
    for i, v in enumerate(vehicles, start=1):
        data.append([
            _p(v["car_color"] or ""),
            _p(v["car_num"] or ""),
            _p(v["car_mark"] or ""),
            _p(v["car_type"] or ""),
            _p(v["customer"] or "", align="RIGHT"),
            _p(_fmt_date(v["date"])),
            str(i),
        ])
    data.append(["", "", "", "", "", ar(f"العدد: {len(vehicles)}"), ar("الإجمالي")])
 
    usable = A4[0] - 2.4 * cm
    # color, plate, mark, type, date, #  (customer flexes)
    fixed = (2.0 + 3.2 + 2.4 + 2.6 + 2.4 + 1.0) * cm
    col_w = [2.0 * cm, 3.2 * cm, 2.4 * cm, 2.6 * cm, None, 2.4 * cm, 1.0 * cm]
    col_w[4] = usable - fixed
 
    t = Table(data, colWidths=col_w, repeatRows=1)
    st = TableStyle(_base_style(brand, font_size=11))
    _zebra(st, len(vehicles))
    st.add("BACKGROUND", (0, -1), (-1, -1), brand)
    st.add("TEXTCOLOR", (0, -1), (-1, -1), colors.white)
    st.add("FONTNAME", (0, -1), (-1, -1), "Amiri-Bold")
    st.add("SPAN", (0, -1), (4, -1))
    t.setStyle(st)
    el.append(t)
    doc.build(el)
 
 
# ==========================================================================
# 4) SUMMARY REPORT  (income + vehicles + trips)
# ==========================================================================
def build_summary_pdf(buf, driver_name, date_from, date_to,
                      total_income, vehicles_count, trips_count):
    brand = colors.HexColor("#0d6efd")
    doc = _doc(buf)
    el = _header(f"ملخص أداء السائق / {driver_name}", date_from, date_to, brand)
 
    rows = [
        [ar("القيمة"), ar("البيان")],
        [f"{float(total_income or 0):,.2f}", ar("إجمالي الدخل")],
        [str(vehicles_count), ar("عدد المركبات المنقولة")],
        [str(trips_count), ar("عدد الرحلات")],
    ]
    usable = A4[0] - 2.4 * cm
    t = Table(rows, colWidths=[6.0 * cm, usable - 6.0 * cm], repeatRows=1)
    st = TableStyle(_base_style(brand, font_size=14))
    st.add("ALIGN", (1, 1), (1, -1), "RIGHT")
    st.add("TOPPADDING", (0, 0), (-1, -1), 12)
    st.add("BOTTOMPADDING", (0, 0), (-1, -1), 12)
    _zebra(st, 3)
    t.setStyle(st)
    el.append(t)
    doc.build(el)
 
 
# ---- self-test -----------------------------------------------------------
if __name__ == "__main__":
    import io, zipfile
    from datetime import datetime
 
    entries = [
        {"account": "فاتورة", "number": 1201, "amount": 120, "created_at": datetime(2026, 5, 14, 9, 30)},
        {"account": "سداد",   "number": 1201, "amount": 100, "created_at": datetime(2026, 5, 15, 11, 0)},
        {"account": "فاتورة", "number": 1202, "amount": 80,  "created_at": datetime(2026, 5, 18, 14, 5)},
    ]
    trips = [
        {"date": datetime(2026, 5, 14), "customer": "بوندد القسطل", "from_location": "عمان",
         "to_location": "الزرقاء", "vehicles": 3, "cost": 45},
        {"date": datetime(2026, 5, 18), "customer": "شركة ياماها", "from_location": "العقبة",
         "to_location": "إربد", "vehicles": 2, "cost": 60},
    ]
    vehicles = [
        {"date": datetime(2026, 5, 14), "customer": "بوندد القسطل", "car_type": "سيدان",
         "car_mark": "تويوتا", "car_num": "12-3456", "car_color": "أبيض"},
        {"date": datetime(2026, 5, 18), "customer": "شركة ياماها", "car_type": "بيك أب",
         "car_mark": "نيسان", "car_num": "45-7890", "car_color": "أسود"},
    ]
 
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, fn in [
            ("account_statement.pdf",
             lambda b: build_account_statement_pdf(b, "أحمد المصري", "2026-05-13", "2026-06-12", entries, 200, 100, 100)),
            ("trips.pdf",
             lambda b: build_trips_pdf(b, "أحمد المصري", "2026-05-13", "2026-06-12", trips, 105)),
            ("vehicles.pdf",
             lambda b: build_vehicles_pdf(b, "أحمد المصري", "2026-05-13", "2026-06-12", vehicles)),
            ("summary.pdf",
             lambda b: build_summary_pdf(b, "أحمد المصري", "2026-05-13", "2026-06-12", 105, 5, 2)),
        ]:
            b = io.BytesIO(); fn(b); z.writestr(name, b.getvalue())
    with open("/tmp/driver_pack.zip", "wb") as f:
        f.write(out.getvalue())
    print("built zip")
 


















