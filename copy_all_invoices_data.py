import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from invoices.models import (
    Invoices, Items, FotarahResponses,
    InvoicesBackup, ItemsBackup, FotarahResponsesBackup
)
from django.db import transaction


def copy_all_tables():
    invoice_map = {}  # old_invoice_id -> new_invoice

    with transaction.atomic():

        # ===============================
        # 1️⃣ Copy Invoices
        # ===============================
        for inv in Invoices.objects.all():
            new_inv = InvoicesBackup.objects.create(
                driver=inv.driver,
                number=inv.number,
                type=inv.type,
                date=inv.date,
                require_id=inv.require_id,
                dinar=inv.dinar,
                fils=inv.fils,
                tamount=inv.tamount,
                samount=inv.samount,
                car=inv.car,
                notes=inv.notes,
                created_at=inv.created_at,
                vehicle=inv.vehicle,
                exported=inv.exported,
                driver_paid=inv.driver_paid,
                customer_paid=inv.customer_paid,
                fotarah_sent=inv.fotarah_sent,
                fotarah_success=inv.fotarah_success,
            )

            invoice_map[inv.id] = new_inv

        print(f"✔ Copied {len(invoice_map)} invoices")

        # ===============================
        # 2️⃣ Copy Items
        # ===============================
        items_bulk = []

        for item in Items.objects.all():
            new_invoice = invoice_map.get(item.number_id)
            if not new_invoice:
                continue

            items_bulk.append(
                ItemsBackup(
                    number=new_invoice,
                    udinar=item.udinar,
                    ufils=item.ufils,
                    qty=item.qty,
                    description=item.description,
                    adinar=item.adinar,
                    afils=item.afils,
                )
            )

        ItemsBackup.objects.bulk_create(items_bulk)
        print(f"✔ Copied {len(items_bulk)} items")

        # ===============================
        # 3️⃣ Copy FotarahResponses
        # ===============================
        responses_bulk = []

        for res in FotarahResponses.objects.all():
            new_invoice = invoice_map.get(res.invoice_id)
            if not new_invoice:
                continue

            responses_bulk.append(
                FotarahResponsesBackup(
                    invoice=new_invoice,
                    success=res.success,
                    message=res.message,
                    fotarah_invoice_id=res.fotarah_invoice_id,
                    qr_code_base64=res.qr_code_base64,
                    qr_code_binary=res.qr_code_binary,
                    response_data=res.response_data,
                    created_at=res.created_at,
                )
            )

        FotarahResponsesBackup.objects.bulk_create(responses_bulk)
        print(f"✔ Copied {len(responses_bulk)} fotarah responses")

    print("🎉 All tables copied successfully!")


if __name__ == "__main__":
    copy_all_tables()
