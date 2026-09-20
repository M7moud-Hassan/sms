"""
Excel twins of driver_reports.py (same brand colours, RTL, zebra, totals).
Signatures match the PDF builders so views can call them symmetrically.
"""
try:
    from . import report_xlsx as rx
except ImportError:            # allows flat import when unit-testing
    import report_xlsx as rx


def build_account_statement_xlsx(buf, driver_name, date_from, date_to,
                                 entries, total_invoiced, total_treasury, required_amount):
    brand = "1f6feb"
    wb, ws = rx.new_sheet("account_statement")
    header = ["التاريخ", "المبلغ", "رقم الفاتورة", "الحركة"]
    r = rx.write_title(ws, brand, f"كشف حركة حساب السائق / {driver_name}",
                       date_from, date_to, len(header))
    rows, pay_idx = [], []
    for e in entries:
        if e["account"] == "سداد":
            pay_idx.append(len(rows))
        rows.append([rx.fmt_date(e["created_at"]),
                     float(e["amount"] or 0),
                     str(e["number"] or ""),
                     e["account"]])
    end = rx.write_table(ws, brand, header, rows, col_widths=[18, 14, 16, 28],
                         start_row=r, number_cols={1})
    rx.highlight_rows(ws, [r + 1 + i for i in pay_idx], len(header), "FFF3CD")
    rx.write_totals(ws, brand, [
        ("إجمالي الفواتير", total_invoiced),
        ("إجمالي المسدد", total_treasury),
        ("المتبقي", required_amount),
    ], start_row=end + 1)
    wb.save(buf)


def build_trips_xlsx(buf, driver_name, date_from, date_to, trips, total_cost):
    brand = "198754"
    wb, ws = rx.new_sheet("trips")
    header = ["التكلفة", "عدد المركبات", "إلى", "من", "العميل", "التاريخ", "#"]
    r = rx.write_title(ws, brand, f"تقرير رحلات السائق / {driver_name}",
                       date_from, date_to, len(header))
    rows = []
    for i, tr in enumerate(trips, start=1):
        rows.append([float(tr["cost"] or 0), tr["vehicles"],
                     tr["to_location"] or "", tr["from_location"] or "",
                     tr["customer"] or "", rx.fmt_date(tr["date"]), i])
    rows.append([float(total_cost or 0), sum(t["vehicles"] for t in trips),
                 "", "", "", f"عدد الرحلات: {len(trips)}", "الإجمالي"])
    end = rx.write_table(ws, brand, header, rows,
                         col_widths=[12, 12, 20, 20, 22, 16, 6],
                         start_row=r, number_cols={0}, total_row=True)
    rx.merge_on_total(ws, len(header), end - 1, 2, 4)   # span إلى/من/العميل
    wb.save(buf)


def build_vehicles_xlsx(buf, driver_name, date_from, date_to, vehicles):
    brand = "6f42c1"
    wb, ws = rx.new_sheet("vehicles")
    header = ["اللون", "رقم اللوحة", "الماركة", "النوع", "العميل", "التاريخ", "#"]
    r = rx.write_title(ws, brand, f"تقرير المركبات المنقولة / {driver_name}",
                       date_from, date_to, len(header))
    rows = []
    for i, v in enumerate(vehicles, start=1):
        rows.append([v["car_color"] or "", v["car_num"] or "", v["car_mark"] or "",
                     v["car_type"] or "", v["customer"] or "", rx.fmt_date(v["date"]), i])
    rows.append(["", "", "", "", "", f"العدد: {len(vehicles)}", "الإجمالي"])
    end = rx.write_table(ws, brand, header, rows,
                         col_widths=[12, 18, 14, 14, 22, 16, 6],
                         start_row=r, total_row=True)
    rx.merge_on_total(ws, len(header), end - 1, 0, 4)
    wb.save(buf)


def build_summary_xlsx(buf, driver_name, date_from, date_to,
                       total_income, vehicles_count, trips_count):
    brand = "0d6efd"
    wb, ws = rx.new_sheet("summary")
    header = ["القيمة", "البيان"]
    r = rx.write_title(ws, brand, f"ملخص أداء السائق / {driver_name}",
                       date_from, date_to, len(header))
    rows = [
        [float(total_income or 0), "إجمالي الدخل"],
        [vehicles_count, "عدد المركبات المنقولة"],
        [trips_count, "عدد الرحلات"],
    ]
    rx.write_table(ws, brand, header, rows, col_widths=[16, 34],
                   start_row=r, number_cols={0}, font_size=14)
    wb.save(buf)
