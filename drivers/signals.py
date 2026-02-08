'''
# drivers/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PMission
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import json

@receiver(post_save, sender=PMission)
def notify_pmission_save(sender, instance, created, **kwargs):
    """Send WebSocket notification when a PMission is created or updated."""
    channel_layer = get_channel_layer()

    # Prepare the data to send over WebSocket
    pmissions = [{
        'id': instance.id,
        'customer_name': instance.customer.name,
        'from_location': instance.from_location,
        'to_location': instance.to_location,
        'car_type': instance.car_type,
        'car_num': instance.car_num
    }]

    # Broadcast the message to the group 'pmissions_group'
    async_to_sync(channel_layer.group_send)(
        "pmissions_group", {
            'type': 'send_pmission_update',
            'pmissions': json.dumps(pmissions),
        }
    )


from django.db.models import F, Q, OuterRef, Subquery
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PMission, SMission

@receiver(post_save, sender=PMission)
def notify_pmission_update(sender, instance, **kwargs):
    # Apply your filter logic to find relevant PMissions
    pmissions = PMission.objects.filter(
        Q(customer__id=instance.customer.id) & (
            Q(mmission__isnull=True) | (
                Q(mmission__smission__car_num=F('car_num')) &
                Q(mmission__smission__receipt__isnull=False)
            )
        )
    ).exclude(mmission__smission__receipt="Invoiced")

    # Annotate the receipt data from SMission
    pmissions = pmissions.annotate(
        smission_receipt=Subquery(
            SMission.objects.filter(mmission=OuterRef('mmission')).values('receipt')[:1]
        )
    )

    # Send the filtered and annotated data via WebSocket
    channel_layer = get_channel_layer()
    if channel_layer:
        for pmission in pmissions:
            async_to_sync(channel_layer.group_send)(
                'pmissions_group', {
                    'type': 'send_pmission_update',
                    'pmission': {
                        'employee': pmission.employee,
                        'notes': pmission.notes,
                        'car_color': pmission.car_color,
                        'car_num': pmission.car_num,
                        'car_mark': pmission.car_mark,
                        'car_type': pmission.car_type,
                        'to_location': pmission.to_location,
                        'from_location': pmission.from_location,
                        'date': pmission.date.strftime('%Y-%m-%d'),
                        'another_notes': pmission.another_notes,
                        'smission_receipt': pmission.smission_receipt,
                        'customer': pmission.customer.name,
                    }
                }
            )

'''