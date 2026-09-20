"""
Excel twins for the customer reports (customer_reports.py `cr`).
Column order / labels follow the data assembled in the customer export view.
Brand colours match the design language of the PDF set; tweak the hex if your
PDFs use different accents.
"""
try:
    from . import report_xlsx as rx
except ImportError:
    import report_xlsx as rx


def build_account_statement_xlsx(buf, customer_name, date_from, date_to,
                                 entries, total_invoiced, total_treasury, required_amount):
    brand = "1f6feb"
    wb, ws = rx.new_sheet("account_statement")
    header = ["التاريخ", "المبلغ", "رقم الفاتورة", "الحركة"]
    r = rx.write_title(ws, brand, f"كشف حساب العميل / {customer_name}",
                       date_from, date_to, len(header))
    rows, pay_idx = [], []
    for e in entries:
        if e["account"] == "سداد":
            pay_idx.append(len(rows))
        rows.append([rx.fmt_date(e["created_at"]), float(e["amount"] or 0),
                     str(e["number"] or ""), e["account"]])
    end = rx.write_table(ws, brand, header, rows, col_widths=[18, 14, 16, 28],
                         start_row=r, number_cols={1})
    rx.highlight_rows(ws, [r + 1 + i for i in pay_idx], len(header), "FFF3CD")
    rx.write_totals(ws, brand, [
        ("إجمالي الفواتير", total_invoiced),
        ("إجمالي المسدد", total_treasury),
        ("المتبقي", required_amount),
    ], start_row=end + 1)
    wb.save(buf)


def build_vehicles_xlsx(buf, customer_name, date_from, date_to, vehicles):
    brand = "6f42c1"
    header = ["اللون", "رقم اللوحة", "الماركة", "النوع", "التاريخ"]
    rows = [[v["car_color"] or "", v["car_num"] or "", v["car_mark"] or "",
             v["car_type"] or "", rx.fmt_date(v["date"])] for v in vehicles]
    rx.simple_report(buf, brand, f"تقرير المركبات المنقولة / {customer_name}",
                     date_from, date_to, header, rows,
                     col_widths=[12, 18, 14, 14, 18], sheet="vehicles")


def build_transactions_xlsx(buf, customer_name, date_from, date_to, txns):
    brand = "0d6efd"
    header = ["رقم", "الماركة", "اللوحة", "المستلم منه", "موقع الاستلام", "وقت الاستلام",
              "المستلم إليه", "موقع التسليم", "وقت التسليم", "السائق"]
    rows = [[t["number"], t["car_mark"] or "", t["car_num"] or "",
             t["from_name"] or "", t["from_location"] or "", rx.fmt_dt(t["from_time"]),
             t["to_name"] or "", t["to_location"] or "", rx.fmt_dt(t["to_time"]),
             t["driver_name"] or ""] for t in txns]
    rx.simple_report(buf, brand, f"حركة النقل التفصيلية / {customer_name}",
                     date_from, date_to, header, rows,
                     col_widths=[10, 12, 14, 16, 18, 16, 16, 18, 16, 16],
                     sheet="transactions")


def build_timeline_xlsx(buf, customer_name, date_from, date_to, tasks):
    brand = "198754"
    header = ["تاريخ الإدخال", "تاريخ البدء", "تاريخ الإنجاز", "الطالب", "رقم الشاصي"]
    rows = [[rx.fmt_dt(t["entered_at"]), rx.fmt_dt(t["start_date"]),
             rx.fmt_dt(t["completion_date"]), t["requester"] or "", t["chassis"] or ""]
            for t in tasks]
    rx.simple_report(buf, brand, f"الجدول الزمني للمهام / {customer_name}",
                     date_from, date_to, header, rows,
                     col_widths=[18, 18, 18, 20, 18], sheet="timeline")


def _invoice_rows(inv_rows):
    return [[r["number"], rx.fmt_date(r["date"]), r.get("driver__name") or "",
             float(r["tamount"] or 0), float(r["customer_paid"] or 0)] for r in inv_rows]


def build_invoices_xlsx(buf, customer_name, date_from, date_to, invoices_all):
    brand = "1f6feb"
    header = ["رقم الفاتورة", "التاريخ", "السائق", "المبلغ", "المدفوع"]
    rx.simple_report(buf, brand, f"فواتير العميل / {customer_name}",
                     date_from, date_to, header, _invoice_rows(invoices_all),
                     number_cols={3, 4}, col_widths=[16, 16, 22, 14, 14],
                     total_label="الإجمالي", total_col=3, sheet="invoices")


def build_outstanding_xlsx(buf, customer_name, date_from, date_to, outstanding_rows):
    brand = "dc3545"
    header = ["رقم الفاتورة", "التاريخ", "السائق", "المبلغ", "المدفوع"]
    rx.simple_report(buf, brand, f"الفواتير غير المسددة / {customer_name}",
                     date_from, date_to, header, _invoice_rows(outstanding_rows),
                     number_cols={3, 4}, col_widths=[16, 16, 22, 14, 14],
                     total_label="الإجمالي", total_col=3, sheet="outstanding")


def build_paid_xlsx(buf, customer_name, date_from, date_to, paid_rows):
    brand = "198754"
    header = ["رقم الفاتورة", "التاريخ", "السائق", "المبلغ", "المدفوع"]
    rx.simple_report(buf, brand, f"الفواتير المسددة / {customer_name}",
                     date_from, date_to, header, _invoice_rows(paid_rows),
                     number_cols={3, 4}, col_widths=[16, 16, 22, 14, 14],
                     total_label="الإجمالي", total_col=3, sheet="paid")


# ---- standalone reports (not from the balance modal) ----
def build_customer_info_xlsx(buf, customers, generated_on):
    brand = "0d6efd"
    header = ["الاسم", "الهاتف", "البريد", "العنوان", "نوع الدفع", "الرصيد"]
    rows = [[c["name"] or "", c["phone"] or "", c["mail"] or "", c["address"] or "",
             c["payment"] or "", float(c["balance"] or 0)] for c in customers]
    rx.simple_report(buf, brand, "بيانات العملاء",
                     generated_on, generated_on, header, rows,
                     number_cols={5}, col_widths=[22, 16, 24, 26, 14, 14],
                     sheet="customers_info")


def build_item_report_xlsx(buf, item_name, date_from, date_to, rows):
    brand = "6f42c1"
    header = ["التاريخ", "المورد", "رقم الفاتورة", "الكمية", "سعر الوحدة", "الإجمالي", "المركبة"]
    data = [[rx.fmt_date(r["date"]), r["supplier_name"] or "", r["invoice_number"],
             r["qty"], float(r["unit_cost"] or 0), float(r["line_total"] or 0),
             r["vehicle"] or ""] for r in rows]
    rx.simple_report(buf, brand, f"تقرير مشتريات الصنف / {item_name}",
                     date_from, date_to, header, data,
                     number_cols={4, 5}, col_widths=[16, 22, 16, 10, 14, 14, 16],
                     total_label="الإجمالي", total_col=5, sheet="item_report")

def build_customer_vehicles_xlsx(buf, customer_name, date_from, date_to, vehicles):
    brand = "0d6efd"
    header = ["عدد النقلات", "اللون", "الماركة", "رقم اللوحة / الشاسيه", "النوع"]
    rows = [[int(v.get("transports", 0) or 0), v["car_color"] or "", v["car_mark"] or "",
             v["car_num"] or "", v["car_type"] or ""] for v in vehicles]
    rx.simple_report(buf, brand, f"مركبات العميل / {customer_name}",
                     date_from, date_to, header, rows,
                     number_cols={0}, col_widths=[12, 12, 16, 22, 14],
                     total_label="إجمالي النقلات", total_col=0, sheet="vehicles")
