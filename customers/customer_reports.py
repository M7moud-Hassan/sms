"""
ReportLab PDF reports for the customer balance page (Arabic / RTL).
 
Builders take plain Python data (lists of dicts) so they stay decoupled
from Django and are easy to test.
 
Dependencies:  pip install reportlab arabic-reshaper python-bidi
Fonts (with Arabic glyphs) in a `fonts/` folder beside this file:
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
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
import arabic_reshaper
from bidi.algorithm import get_display
 
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
pdfmetrics.registerFont(TTFont("Amiri", os.path.join(FONT_DIR, "Amiri-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Amiri-Bold", os.path.join(FONT_DIR, "Amiri-Bold.ttf")))
pdfmetrics.registerFontFamily("Amiri", normal="Amiri", bold="Amiri-Bold")
 
 
def ar(text):
    if text is None:
        return ""
    return get_display(arabic_reshaper.reshape(str(text)))
 
 
def _fmt_date(d):
    return d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else (str(d) if d else "")
 
 
def _fmt_dt(dt):
    return dt.strftime("%Y-%m-%d %H:%M") if hasattr(dt, "strftime") else (str(dt) if dt else "")
 
 
GRID = colors.HexColor("#d0d0d0")
ZEBRA = colors.HexColor("#f4f7fb")
 
 
def _p(text, align="CENTER", size=10):
    style = ParagraphStyle("cell", fontName="Amiri", fontSize=size, leading=size + 3,
                           alignment=TA_RIGHT if align == "RIGHT" else TA_CENTER, wordWrap="CJK")
    return Paragraph(ar(text), style)
 
 
def _header(title, date_from, date_to, brand, subtitle=None):
    h = ParagraphStyle("h", fontName="Amiri-Bold", fontSize=18, textColor=brand,
                       alignment=TA_RIGHT, leading=22)
    r = ParagraphStyle("r", fontName="Amiri", fontSize=11,
                       textColor=colors.HexColor("#555555"), alignment=TA_RIGHT, leading=15)
    sub = subtitle if subtitle is not None else f"من {date_from} إلى {date_to}"
    return [Paragraph(ar(title), h), Spacer(1, 3),
            Paragraph(ar(sub), r), Spacer(1, 10)]
 
 
def _build_table_report(buf, title, date_from, date_to, columns, data, brand_hex,
                        landscape_mode=False, totals=None, font_size=10, subtitle=None):
    """
    columns: list of (label, key, width_cm_or_None, align 'C'/'R', wrap bool)
             listed LEFT-TO-RIGHT as they appear on the page (RTL: '#' is last).
    data:    list of dicts keyed by the column keys.
    totals:  optional list aligned to columns; '' for empty cells. Rendered as a
             coloured footer row.
    """
    brand = colors.HexColor(brand_hex)
    page = landscape(A4) if landscape_mode else A4
    doc = SimpleDocTemplate(buf, pagesize=page, topMargin=1.1 * cm, bottomMargin=1.1 * cm,
                            leftMargin=1.2 * cm, rightMargin=1.2 * cm, title="report")
    elements = _header(title, date_from, date_to, brand, subtitle=subtitle)
 
    usable = page[0] - 2.4 * cm
    fixed = sum(c[2] for c in columns if c[2]) * cm
    n_flex = sum(1 for c in columns if not c[2])
    flex_w = (usable - fixed) / n_flex if n_flex else 0
    col_w = [(c[2] * cm if c[2] else flex_w) for c in columns]
 
    head = [ar(c[0]) for c in columns]
    rows = [head]
    for d in data:
        row = []
        for (label, key, w, align, wrap) in columns:
            val = d.get(key, "")
            if wrap:
                row.append(_p(val, align="RIGHT" if align == "R" else "CENTER", size=font_size))
            else:
                row.append(val if isinstance(val, str) else str(val))
        rows.append(row)
 
    n_data = len(data)
    if totals:
        rows.append([_p(x, size=font_size) if (isinstance(x, str) and x) else (x or "") for x in totals])
 
    t = Table(rows, colWidths=col_w, repeatRows=1)
    st = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Amiri"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("GRID", (0, 0), (-1, -1), 0.75, GRID),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, 0), (-1, 0), brand),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Amiri-Bold"),
    ])
    for i in range(1, n_data + 1):              # zebra on data rows
        if i % 2 == 0:
            st.add("BACKGROUND", (0, i), (-1, i), ZEBRA)
    if totals:
        st.add("BACKGROUND", (0, -1), (-1, -1), brand)
        st.add("TEXTCOLOR", (0, -1), (-1, -1), colors.white)
        st.add("FONTNAME", (0, -1), (-1, -1), "Amiri-Bold")
    t.setStyle(st)
    elements.append(t)
    doc.build(elements)
 
 
# ==========================================================================
# 0) ACCOUNT STATEMENT  (existing كشف حركة الحساب)
# ==========================================================================
def build_account_statement_pdf(buf, customer_name, date_from, date_to,
                                entries, total_invoiced, total_treasury, required_amount):
    for e in entries:
        e["_amount"] = f"{float(e['amount'] or 0):,.2f}"
        e["_date"] = _fmt_dt(e["created_at"])
        e["_num"] = str(e["number"] or "")
    columns = [
        ("التاريخ", "_date", 5.0, "C", True),
        ("المبلغ", "_amount", 4.0, "C", False),
        ("رقم الفاتورة", "_num", 4.0, "C", False),
        ("الحركة", "account", None, "C", True),
    ]
    totals = ["", "", f"{float(required_amount):,.2f}", "المتبقي"]
    _build_table_report(buf, f"كشف حركة حساب العميل / {customer_name}",
                        date_from, date_to, columns, entries, "#1f6feb",
                        totals=totals, font_size=11)
 
 
# ==========================================================================
# 1) VEHICLES TRANSPORTED  (number, type, registration)
# ==========================================================================
def build_vehicles_pdf(buf, customer_name, date_from, date_to, vehicles):
    for v in vehicles:
        v["_date"] = _fmt_date(v["date"])
    columns = [
        ("اللون", "car_color", 2.2, "C", True),
        ("رقم اللوحة / الشاسيه", "car_num", 3.4, "C", True),
        ("الماركة", "car_mark", 2.6, "C", True),
        ("النوع", "car_type", 3.0, "C", True),
        ("التاريخ", "_date", 2.6, "C", True),
        ("#", "_i", 1.0, "C", False),
    ]
    for i, v in enumerate(vehicles, 1):
        v["_i"] = str(i)
    totals = ["", "", "", "", f"العدد: {len(vehicles)}", ""]
    _build_table_report(buf, f"تقرير المركبات المنقولة للعميل / {customer_name}",
                        date_from, date_to, columns, vehicles, "#6f42c1", totals=totals)
 
 
# ==========================================================================
# 2) TRANSPORT TRANSACTIONS  (full lifecycle, landscape)
# ==========================================================================
def build_transactions_pdf(buf, customer_name, date_from, date_to, txns):
    for i, x in enumerate(txns, 1):
        x["_i"] = str(i)
        x["_num"] = str(x.get("number") or "")
        x["_veh"] = f'{x.get("car_mark") or ""} {x.get("car_num") or ""}'.strip()
        x["_from_t"] = _fmt_dt(x.get("from_time"))
        x["_to_t"] = _fmt_dt(x.get("to_time"))
    columns = [
        ("السائق", "driver_name", None, "C", True),
        ("وقت التسليم", "_to_t", 3.2, "C", True),
        ("موقع التسليم", "to_location", None, "C", True),
        ("المستلم", "to_name", None, "C", True),
        ("وقت الاستلام", "_from_t", 3.2, "C", True),
        ("موقع الاستلام", "from_location", None, "C", True),
        ("المرسِل", "from_name", None, "C", True),
        ("المركبة", "_veh", None, "C", True),
        ("سند رقم", "_num", 2.0, "C", False),
        ("#", "_i", 0.9, "C", False),
    ]
    totals = ["", "", "", "", "", "", "", "", f"العدد: {len(txns)}", ""]
    _build_table_report(buf, f"تقرير معاملات النقل للعميل / {customer_name}",
                        date_from, date_to, columns, txns, "#198754",
                        landscape_mode=True, totals=totals, font_size=9)
 
 
# ==========================================================================
# 3) TASK TIMELINE  (entry / start / completion + requester + chassis)
# ==========================================================================
def build_timeline_pdf(buf, customer_name, date_from, date_to, tasks):
    for i, t in enumerate(tasks, 1):
        t["_i"] = str(i)
        t["_entered"] = _fmt_dt(t.get("entered_at"))
        t["_start"] = _fmt_dt(t.get("start_date"))
        t["_done"] = _fmt_dt(t.get("completion_date"))
    columns = [
        ("وقت/تاريخ الإنجاز", "_done", 3.4, "C", True),
        ("وقت/تاريخ البدء", "_start", 3.4, "C", True),
        ("وقت/تاريخ الإدخال", "_entered", 3.4, "C", True),
        ("رقم الشاسيه", "chassis", None, "C", True),
        ("طالب الخدمة", "requester", None, "C", True),
        ("#", "_i", 1.0, "C", False),
    ]
    _build_table_report(buf, f"تقرير زمن تنفيذ المهام للعميل / {customer_name}",
                        date_from, date_to, columns, tasks, "#fd7e14", font_size=10)
 
 
# ==========================================================================
# 4/5/6) INVOICE TABLES  (all / outstanding / paid)
# ==========================================================================
def _invoice_report(buf, title, customer_name, date_from, date_to, invoices, brand,
                    show_remaining=False):
    rows = []
    total_amount = 0.0
    total_rem = 0.0
    for i, inv in enumerate(invoices, 1):
        amt = float(inv.get("tamount") or 0)
        paid = float(inv.get("customer_paid") or 0)
        rem = amt - paid
        total_amount += amt
        total_rem += rem
        rows.append({
            "_i": str(i),
            "_num": str(inv.get("number") or ""),
            "_date": _fmt_date(inv.get("date")),
            "driver__name": inv.get("driver__name") or "",
            "_amt": f"{amt:,.2f}",
            "_paid": f"{paid:,.2f}",
            "_rem": f"{rem:,.2f}",
        })
    columns = [
        ("المبلغ", "_amt", 3.2, "C", False),
    ]
    if show_remaining:
        columns += [("المسدّد", "_paid", 3.0, "C", False),
                    ("المتبقي", "_rem", 3.0, "C", False)]
    columns += [
        ("السائق", "driver__name", None, "C", True),
        ("التاريخ", "_date", 2.6, "C", True),
        ("رقم الفاتورة", "_num", 2.6, "C", False),
        ("#", "_i", 1.0, "C", False),
    ]
    if show_remaining:
        totals = [f"{total_amount:,.2f}", "", f"{total_rem:,.2f}", "", "", "", f"العدد: {len(rows)}"]
        # pad/align totals to column count
        totals = [f"{total_amount:,.2f}", "", f"{total_rem:,.2f}", "", "", f"العدد: {len(rows)}", ""]
    else:
        totals = [f"{total_amount:,.2f}", "", "", "", f"العدد: {len(rows)}", ""]
    _build_table_report(buf, title, date_from, date_to, columns, rows, brand,
                        totals=totals, font_size=10)
 
 
def build_invoices_pdf(buf, customer_name, date_from, date_to, invoices):
    _invoice_report(buf, f"تقرير فواتير العميل / {customer_name}",
                    customer_name, date_from, date_to, invoices, "#1f6feb")
 
 
def build_outstanding_pdf(buf, customer_name, date_from, date_to, invoices):
    _invoice_report(buf, f"تقرير الفواتير غير المسددة للعميل / {customer_name}",
                    customer_name, date_from, date_to, invoices, "#dc3545",
                    show_remaining=True)
 
 
def build_paid_pdf(buf, customer_name, date_from, date_to, invoices):
    _invoice_report(buf, f"تقرير الفواتير المسددة للعميل / {customer_name}",
                    customer_name, date_from, date_to, invoices, "#198754",
                    show_remaining=True)
 
 
# ==========================================================================
# 7) CUSTOMER INFORMATION  (all customers: contact details, landscape)
# ==========================================================================
def build_customer_info_pdf(buf, customers, generated_on=""):
    """customers: list of dicts {name, phone, mail, address, payment, balance}."""
    rows = []
    for i, c in enumerate(customers, 1):
        rows.append({
            "_i": str(i),
            "name": c.get("name") or "",
            "phone": c.get("phone") or "",
            "mail": c.get("mail") or "",
            "address": c.get("address") or "",
            "payment": c.get("payment") or "",
            "_bal": f"{float(c.get('balance') or 0):,.2f}",
        })
    columns = [
        ("الرصيد", "_bal", 2.6, "C", False),
        ("نظام الدفع", "payment", 2.6, "C", True),
        ("البريد الإلكتروني", "mail", None, "C", True),
        ("الهاتف", "phone", 3.4, "C", True),
        ("العنوان", "address", None, "C", True),
        ("اسم العميل", "name", None, "R", True),
        ("#", "_i", 1.0, "C", False),
    ]
    totals = ["", "", "", "", "", f"عدد العملاء: {len(rows)}", ""]
    sub = f"عدد العملاء: {len(customers)}"
    if generated_on:
        sub += f" — {generated_on}"
    _build_table_report(buf, "تقرير معلومات العملاء", "", "", columns, rows, "#0d6efd",
                        landscape_mode=True, totals=totals, font_size=10, subtitle=sub)
 
# ==========================================================================
# 8) VEHICLE EXPENSES over a period
# ==========================================================================
def build_vehicle_expenses_pdf(buf, vehicle_number, date_from, date_to, rows):
    """rows: list of {number, date, supplier_name, description, amount}"""
    data = []
    total = 0.0
    for i, r in enumerate(rows, 1):
        amt = float(r.get("amount") or 0)
        total += amt
        data.append({
            "_i": str(i),
            "_num": str(r.get("number") or ""),
            "_date": _fmt_date(r.get("date")),
            "supplier_name": r.get("supplier_name") or "",
            "description": r.get("description") or "",
            "_amt": f"{amt:,.2f}",
        })
    columns = [
        ("المبلغ", "_amt", 3.2, "C", False),
        ("البيان", "description", None, "C", True),
        ("المورّد", "supplier_name", None, "C", True),
        ("التاريخ", "_date", 2.8, "C", True),
        ("رقم الفاتورة", "_num", 2.6, "C", False),
        ("#", "_i", 1.0, "C", False),
    ]
    totals = [f"{total:,.2f}", "", "", "", f"العدد: {len(data)}", ""]
    _build_table_report(buf, f"تقرير مصاريف المركبة / {vehicle_number}",
                        date_from, date_to, columns, data, "#dc3545",
                        totals=totals, font_size=10)


# ==========================================================================
# 9) VEHICLE REVENUE over a period
# ==========================================================================
def build_vehicle_revenue_pdf(buf, vehicle_number, date_from, date_to, rows):
    """rows: list of {number, date, customer_name, amount}"""
    data = []
    total = 0.0
    for i, r in enumerate(rows, 1):
        amt = float(r.get("amount") or 0)
        total += amt
        data.append({
            "_i": str(i),
            "_num": str(r.get("number") or ""),
            "_date": _fmt_date(r.get("date")),
            "customer_name": r.get("customer_name") or "",
            "_amt": f"{amt:,.2f}",
        })
    columns = [
        ("المبلغ", "_amt", 3.4, "C", False),
        ("العميل", "customer_name", None, "C", True),
        ("التاريخ", "_date", 2.8, "C", True),
        ("رقم الفاتورة", "_num", 2.8, "C", False),
        ("#", "_i", 1.0, "C", False),
    ]
    totals = [f"{total:,.2f}", "", "", f"العدد: {len(data)}", ""]
    _build_table_report(buf, f"تقرير إيرادات المركبة / {vehicle_number}",
                        date_from, date_to, columns, data, "#198754",
                        totals=totals, font_size=10)


# ==========================================================================
# 10) FUEL CONSUMPTION per vehicle (km / litre) over a period
#     segments: per-fill dicts {date, odo_prev, odo_curr, litres}
#     km = odo_curr - odo_prev ;  km/L = km / litres
# ==========================================================================
def build_fuel_consumption_pdf(buf, vehicle_number, date_from, date_to, segments):
    data = []
    total_km = 0.0
    total_litres = 0.0
    for i, s in enumerate(segments, 1):
        odo_prev = s.get("odo_prev")
        odo_curr = float(s.get("odo_curr") or 0)
        litres = float(s.get("litres") or 0)
        if odo_prev is None:                       # first fill: no previous reading
            km = None
            kmpl = None
        else:
            km = odo_curr - float(odo_prev)
            kmpl = (km / litres) if litres else None
            total_km += km
            total_litres += litres
        data.append({
            "_i": str(i),
            "_date": _fmt_dt(s.get("date")),
            "_odo_prev": "—" if odo_prev is None else f"{float(odo_prev):,.0f}",
            "_odo": f"{odo_curr:,.0f}",
            "_km": "—" if km is None else f"{km:,.0f}",
            "_litres": f"{litres:,.2f}",
            "_kmpl": "—" if kmpl is None else f"{kmpl:,.2f}",
        })
    avg = (total_km / total_litres) if total_litres else 0
    columns = [
        ("كم/لتر", "_kmpl", 2.4, "C", False),
        ("اللترات", "_litres", 2.4, "C", False),
        ("المسافة (كم)", "_km", 2.6, "C", False),
        ("العداد الحالي", "_odo", 2.8, "C", True),
        ("العداد السابق", "_odo_prev", 2.8, "C", True),
        ("التاريخ", "_date", 3.4, "C", True),
        ("#", "_i", 1.0, "C", False),
    ]
    totals = [f"{avg:,.2f}", f"{total_litres:,.2f}", f"{total_km:,.0f}", "", "", "المعدل/الإجمالي", ""]
    sub = f"من {date_from} إلى {date_to} — متوسط الاستهلاك: {avg:,.2f} كم/لتر"
    _build_table_report(buf, f"تقرير استهلاك الوقود للمركبة / {vehicle_number}",
                        date_from, date_to, columns, data, "#0d6efd",
                        totals=totals, font_size=10, subtitle=sub)


# ==========================================================================
# 11) DETAILED MAINTENANCE — parts used + cost of each part
#     rows: {date, maintenance_center, part_name, qty, unit_cost}
# ==========================================================================
def build_maintenance_parts_pdf(buf, vehicle_number, date_from, date_to, rows):
    data = []
    grand = 0.0
    for i, r in enumerate(rows, 1):
        qty = float(r.get("qty") or 0)
        unit = float(r.get("unit_cost") or 0)
        line = qty * unit
        grand += line
        data.append({
            "_i": str(i),
            "_date": _fmt_date(r.get("date")),
            "maintenance_center": r.get("maintenance_center") or "",
            "part_name": r.get("part_name") or "",
            "_qty": f"{qty:,.0f}",
            "_unit": f"{unit:,.2f}",
            "_cost": f"{line:,.2f}",
        })
    columns = [
        ("التكلفة", "_cost", 2.8, "C", False),
        ("سعر الوحدة", "_unit", 2.6, "C", False),
        ("الكمية", "_qty", 1.8, "C", False),
        ("القطعة", "part_name", None, "C", True),
        ("مركز الصيانة", "maintenance_center", None, "C", True),
        ("التاريخ", "_date", 2.8, "C", True),
        ("#", "_i", 1.0, "C", False),
    ]
    totals = [f"{grand:,.2f}", "", "", "", "", f"عدد القطع: {len(data)}", ""]
    _build_table_report(buf, f"تقرير صيانة المركبة التفصيلي / {vehicle_number}",
                        date_from, date_to, columns, data, "#fd7e14",
                        totals=totals, font_size=10)

# ==========================================================================
# 12) SUPPLIER DETAILED INVOICES over a period
#     invoices: {number, date, type, tamount, paid, notes}
# ==========================================================================
def build_supplier_invoices_pdf(buf, supplier_name, date_from, date_to, invoices):
    data = []
    total_amt = 0.0
    total_paid = 0.0
    for i, inv in enumerate(invoices, 1):
        amt = float(inv.get("tamount") or 0)
        paid = float(inv.get("paid") or 0)
        rem = amt - paid
        total_amt += amt
        total_paid += paid
        data.append({
            "_i": str(i),
            "_num": str(inv.get("number") or ""),
            "_date": _fmt_date(inv.get("date")),
            "type": inv.get("type") or "",
            "notes": inv.get("notes") or "",
            "_amt": f"{amt:,.2f}",
            "_paid": f"{paid:,.2f}",
            "_rem": f"{rem:,.2f}",
        })
    columns = [
        ("المتبقي", "_rem", 2.6, "C", False),
        ("المسدّد", "_paid", 2.6, "C", False),
        ("المبلغ", "_amt", 2.8, "C", False),
        ("ملاحظات", "notes", None, "C", True),
        ("النظام", "type", 2.2, "C", True),
        ("التاريخ", "_date", 2.6, "C", True),
        ("رقم الفاتورة", "_num", 2.6, "C", False),
        ("#", "_i", 0.9, "C", False),
    ]
    total_rem = total_amt - total_paid
    totals = [f"{total_rem:,.2f}", f"{total_paid:,.2f}", f"{total_amt:,.2f}",
              "", "", "", f"العدد: {len(data)}", ""]
    _build_table_report(buf, f"تقرير فواتير المورّد التفصيلي / {supplier_name}",
                        date_from, date_to, columns, data, "#0d6efd",
                        landscape_mode=True, totals=totals, font_size=10)


# ==========================================================================
# 13) ITEM PURCHASE HISTORY across all suppliers (per item, regardless of supplier)
#     rows: {date, supplier_name, invoice_number, qty, unit_cost, line_total, vehicle}
# ==========================================================================
def build_item_report_pdf(buf, item_name, date_from, date_to, rows):
    data = []
    total_qty = 0.0
    grand = 0.0
    for i, r in enumerate(rows, 1):
        qty = float(r.get("qty") or 0)
        line = float(r.get("line_total") or 0)
        total_qty += qty
        grand += line
        data.append({
            "_i": str(i),
            "_date": _fmt_date(r.get("date")),
            "supplier_name": r.get("supplier_name") or "",
            "_num": str(r.get("invoice_number") or ""),
            "vehicle": r.get("vehicle") or "",
            "_qty": f"{qty:,.0f}",
            "_unit": f"{float(r.get('unit_cost') or 0):,.2f}",
            "_line": f"{line:,.2f}",
        })
    columns = [
        ("الإجمالي", "_line", 2.8, "C", False),
        ("سعر الوحدة", "_unit", 2.6, "C", False),
        ("الكمية", "_qty", 1.8, "C", False),
        ("المركبة", "vehicle", None, "C", True),
        ("المورّد", "supplier_name", None, "C", True),
        ("رقم الفاتورة", "_num", 2.6, "C", False),
        ("التاريخ", "_date", 2.6, "C", True),
        ("#", "_i", 0.9, "C", False),
    ]
    totals = [f"{grand:,.2f}", "", f"{total_qty:,.0f}", "", "", "", f"العدد: {len(data)}", ""]
    sub = f"من {date_from} إلى {date_to} — إجمالي الكمية: {total_qty:,.0f} — إجمالي القيمة: {grand:,.2f}"
    _build_table_report(buf, f"تقرير مشتريات الصنف / {item_name}",
                        date_from, date_to, columns, data, "#6f42c1",
                        landscape_mode=True, totals=totals, font_size=10, subtitle=sub)
    
# ---- self-test -----------------------------------------------------------
if __name__ == "__main__":
    import io, zipfile
    from datetime import datetime
    cn, df, dt = "شركة ياماها المعرض", "2025-01-01", "2026-06-12"
 
    entries = [
        {"account": "فاتورة", "number": 1201, "amount": 120, "created_at": datetime(2026, 5, 14, 9, 30)},
        {"account": "سداد", "number": 1201, "amount": 100, "created_at": datetime(2026, 5, 15, 11, 0)},
    ]
    vehicles = [
        {"date": datetime(2025, 9, 14), "car_type": "Motorcycle", "car_mark": "N-Max",
         "car_num": "MH3SG5680RK219340", "car_color": "BALCK"},
        {"date": datetime(2025, 10, 6), "car_type": "Motorcycle", "car_mark": "nm",
         "car_num": "MH3SG5680RK236894", "car_color": "black"},
    ]
    txns = [
        {"number": 5001, "car_mark": "N-Max", "car_num": "MH3SG5680RK219340",
         "from_name": "خالد", "from_location": "المعرض ش مكة", "from_time": datetime(2025, 9, 14, 8, 0),
         "to_name": "سامي", "to_location": "صيانة ياماها - البيادر", "to_time": datetime(2025, 9, 14, 12, 30),
         "driver_name": "محمد حمدان"},
    ]
    tasks = [
        {"entered_at": datetime(2025, 9, 13, 16, 5), "start_date": datetime(2025, 9, 14),
         "completion_date": datetime(2025, 9, 14), "requester": "م. أحمد",
         "chassis": "MH3SG5680RK219340"},
    ]
    invs = [
        {"number": 1201, "date": datetime(2026, 5, 14), "driver__name": "محمد حمدان",
         "tamount": 120, "customer_paid": 100},
        {"number": 1202, "date": datetime(2026, 5, 18), "driver__name": "علي",
         "tamount": 80, "customer_paid": 80},
    ]
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, fn in [
            ("account_statement.pdf", lambda b: build_account_statement_pdf(b, cn, df, dt, entries, 120, 100, 20)),
            ("vehicles.pdf", lambda b: build_vehicles_pdf(b, cn, df, dt, vehicles)),
            ("transactions.pdf", lambda b: build_transactions_pdf(b, cn, df, dt, txns)),
            ("timeline.pdf", lambda b: build_timeline_pdf(b, cn, df, dt, tasks)),
            ("invoices.pdf", lambda b: build_invoices_pdf(b, cn, df, dt, invs)),
            ("outstanding.pdf", lambda b: build_outstanding_pdf(b, cn, df, dt, [i for i in invs if float(i['tamount']) > float(i['customer_paid'])])),
            ("paid.pdf", lambda b: build_paid_pdf(b, cn, df, dt, [i for i in invs if float(i['customer_paid']) >= float(i['tamount'])])),
        ]:
            b = io.BytesIO(); fn(b); z.writestr(name, b.getvalue())
    open("/tmp/customer_pack.zip", "wb").write(out.getvalue())
    print("built zip")

def build_customer_vehicles_pdf(buf, customer_name, date_from, date_to, vehicles):
    """Customer Vehicles table (with transport counts) — matches the details page."""
    for i, v in enumerate(vehicles, 1):
        v["_i"] = str(i)
        v["_transports"] = str(v.get("transports", 0))
    columns = [
        ("عدد النقلات", "_transports", 2.4, "C", True),
        ("اللون", "car_color", 2.4, "C", True),
        ("الماركة", "car_mark", 2.8, "C", True),
        ("رقم اللوحة / الشاسيه", "car_num", 3.6, "C", True),
        ("النوع", "car_type", 3.0, "C", True),
        ("#", "_i", 1.0, "C", False),
    ]
    total_transports = sum(int(v.get("transports", 0) or 0) for v in vehicles)
    totals = [str(total_transports), "", "", "", f"العدد: {len(vehicles)}", ""]
    _build_table_report(buf, f"مركبات العميل / {customer_name}",
                        date_from, date_to, columns, vehicles, "#0d6efd", totals=totals)