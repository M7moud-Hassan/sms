"""Excel twins for the vehicle reports."""
try:
    from . import report_xlsx as rx
except ImportError:
    import report_xlsx as rx


def build_vehicle_revenue_xlsx(buf, vehicle_number, date_from, date_to, revenue_rows):
    brand = "17a2b8"
    header = ["رقم الفاتورة", "التاريخ", "العميل", "المبلغ"]
    rows = [[r["number"], rx.fmt_date(r["date"]), r["customer_name"] or "",
             float(r["amount"] or 0)] for r in revenue_rows]
    rx.simple_report(buf, brand, f"إيرادات المركبة / {vehicle_number}",
                     date_from, date_to, header, rows,
                     number_cols={3}, col_widths=[16, 16, 24, 14],
                     total_label="إجمالي الإيراد", total_col=3, sheet="revenue")


def build_vehicle_expenses_xlsx(buf, vehicle_number, date_from, date_to, expenses_rows):
    brand = "dc3545"
    header = ["رقم الفاتورة", "التاريخ", "المورد", "البيان", "المبلغ"]
    rows = [[r["number"], rx.fmt_date(r["date"]), r["supplier_name"] or "",
             r["description"] or "", float(r["amount"] or 0)] for r in expenses_rows]
    rx.simple_report(buf, brand, f"مصروفات المركبة / {vehicle_number}",
                     date_from, date_to, header, rows,
                     number_cols={4}, col_widths=[16, 16, 22, 26, 14],
                     total_label="إجمالي المصروف", total_col=4, sheet="expenses")


def build_fuel_consumption_xlsx(buf, vehicle_number, date_from, date_to, segments):
    brand = "0d6efd"
    header = ["التاريخ", "العداد السابق", "العداد الحالي", "المسافة", "اللترات", "كم/لتر"]
    rows = []
    for s in segments:
        prev, curr, litres = s["odo_prev"], s["odo_curr"], s["litres"]
        dist = ""
        kmpl = ""
        if prev is not None and curr is not None:
            try:
                d = float(curr) - float(prev)
                dist = d
                if litres:
                    kmpl = round(d / float(litres), 2)
            except (TypeError, ValueError):
                pass
        rows.append([rx.fmt_date(s["date"]),
                     float(prev) if prev is not None else "",
                     float(curr) if curr is not None else "",
                     dist,
                     float(litres) if litres is not None else "",
                     kmpl])
    rx.simple_report(buf, brand, f"استهلاك الوقود / {vehicle_number}",
                     date_from, date_to, header, rows,
                     number_cols={1, 2, 3, 4, 5}, col_widths=[16, 14, 14, 12, 12, 12],
                     sheet="fuel")


def build_maintenance_parts_xlsx(buf, vehicle_number, date_from, date_to, maintenance_rows):
    brand = "6f42c1"
    header = ["التاريخ", "مركز الصيانة", "القطعة", "الكمية", "سعر الوحدة", "الإجمالي"]
    rows = []
    for r in maintenance_rows:
        qty = r["qty"] or 0
        unit = float(r["unit_cost"] or 0)
        rows.append([rx.fmt_date(r["date"]), r["maintenance_center"] or "",
                     r["part_name"] or "", qty, unit, float(qty) * unit])
    rx.simple_report(buf, brand, f"قطع وتكاليف الصيانة / {vehicle_number}",
                     date_from, date_to, header, rows,
                     number_cols={4, 5}, col_widths=[16, 22, 22, 10, 14, 14],
                     total_label="الإجمالي", total_col=5, sheet="maintenance")
