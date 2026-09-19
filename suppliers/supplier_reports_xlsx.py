"""Excel twins for the supplier reports."""
try:
    from . import report_xlsx as rx
except ImportError:
    import report_xlsx as rx


def build_account_statement_xlsx(buf, supplier_name, date_from, date_to,
                                 entries, total_inv, total_pay, required_amount):
    brand = "1f6feb"
    wb, ws = rx.new_sheet("account_statement")
    header = ["التاريخ", "المبلغ", "رقم الفاتورة", "الحركة"]
    r = rx.write_title(ws, brand, f"كشف حساب المورد / {supplier_name}",
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
        ("إجمالي الفواتير", total_inv),
        ("إجمالي المسدد", total_pay),
        ("المتبقي", required_amount),
    ], start_row=end + 1)
    wb.save(buf)


def build_supplier_invoices_xlsx(buf, supplier_name, date_from, date_to, inv_rows):
    brand = "198754"
    header = ["رقم الفاتورة", "التاريخ", "النوع", "المبلغ", "المدفوع", "ملاحظات"]
    rows = [[r["number"], rx.fmt_date(r["date"]), r["type"] or "",
             float(r["tamount"] or 0), float(r["paid"] or 0), r["notes"] or ""]
            for r in inv_rows]
    rx.simple_report(buf, brand, f"فواتير المورد التفصيلية / {supplier_name}",
                     date_from, date_to, header, rows,
                     number_cols={3, 4}, col_widths=[16, 16, 14, 14, 14, 28],
                     total_label="الإجمالي", total_col=3, sheet="supplier_invoices")
