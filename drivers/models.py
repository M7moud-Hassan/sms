from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
import json
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from datetime import datetime
from customers.models import Customers

# Create your models here.
class Drivers(models.Model):
    name = models.CharField(unique=True, null=True, max_length=200)
    status = models.CharField(null=True, blank=True, max_length=20, default="Available")
    username = models.CharField(null=True, max_length=20)
    password = models.CharField(null=True, max_length=20)
    balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_by = models.CharField(blank=True, null=True, max_length=50)
    created_at = models.DateTimeField(default=datetime.now)
    class Meta:
        unique_together = ('username', 'password',)
    def __str__(self):
        return self.name

class Treasury(models.Model):
    driver = models.ForeignKey(Drivers, on_delete=models.CASCADE, null=True)
    invoice = models.ForeignKey('invoices.Invoices', on_delete=models.CASCADE, null=True, related_name='driver_treasury')
    number = models.IntegerField(unique=True, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    payment = models.CharField(null=True, max_length=10)
    created_by = models.CharField(blank=True, null=True, max_length=50)
    created_at = models.DateTimeField(default=datetime.now)
    def __str__(self):
        return self.driver.name

class MMission(models.Model):
    description = models.CharField(blank=True, null=True, max_length=50)
    driver = models.ForeignKey(Drivers, on_delete=models.CASCADE, null=True)
    customer = models.ForeignKey(Customers, on_delete=models.CASCADE, null=True)
    date = models.DateField(null=True, blank=True)
    from_location = models.CharField(null=True, blank=True, max_length=50)
    to_location = models.CharField(null=True, blank=True, max_length=50)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    notes = models.CharField(blank=True, null=True, max_length=500)
    receipt = models.CharField(null=True, blank=True, max_length=20)
    scost = models.CharField(null=True, blank=True, max_length=100)
    count = models.IntegerField(null=True, blank=True, default=0)
    accept = models.CharField(null=True, blank=True, max_length=20)
    created_by = models.CharField(blank=True, null=True, max_length=50)
    created_at = models.DateTimeField(default=datetime.now)
    def __str__(self):
        return str(self.id)

class PMission(models.Model):
    mmission = models.ForeignKey(MMission, on_delete=models.CASCADE, null=True, blank=True)
    customer = models.ForeignKey(Customers, on_delete=models.CASCADE, null=True)
    employee = models.CharField(blank=True, null=True, max_length=50)
    date = models.DateField(null=True, blank=True)
    from_location = models.CharField(null=True, blank=True, max_length=50)
    to_location = models.CharField(null=True, blank=True, max_length=50)
    car_type = models.CharField(null=True, max_length=50)
    car_mark = models.CharField(null=True, max_length=50)
    car_num = models.CharField(null=True, blank=True, max_length=50)
    car_color = models.CharField(null=True, blank=True, max_length=50)
    notes = models.CharField(blank=True, null=True, max_length=500)
    another_notes = models.CharField(blank=True, null=True, max_length=500)
    created_at = models.DateTimeField(default=datetime.now)
    read = models.BooleanField(default=False)
    def __str__(self):
        return self.employee

    def save(self, *args, **kwargs):
        # Get the old instance for comparison
        if self.pk:  # Only compare if the instance already exists
            old_instance = PMission.objects.get(pk=self.pk)
        else:
            old_instance = None
        super().save(*args, **kwargs)

        # If it's a new instance (creation), send a notification
        if old_instance is None:
            self.send_notification()
        else:
            # If old_instance exists, check if any fields besides 'mmission' and 'another_notes' were changed
            fields_to_check = ['customer', 'employee', 'date', 'from_location', 'to_location', 'car_type', 'car_mark',
                               'car_num', 'car_color', 'notes']
            changes_detected = any(getattr(self, field) != getattr(old_instance, field) for field in fields_to_check)
            if changes_detected:
                self.send_notification()

    def send_notification(self):
        # Example of sending an array of PMission notifications
        channel_layer = get_channel_layer()
        # Collecting multiple missions (you can modify this query as needed)
        pmissions = PMission.objects.filter(read=False)  # Example: sending all unread missions
        notification_data = []
        for mission in pmissions:
            notification_data.append({
                'id': mission.id,
                'customer_name': mission.customer.name if mission.customer else 'N/A',
                'from_location': mission.from_location,
                'to_location': mission.to_location,
                'car_type': mission.car_type,
                'car_num': mission.car_num,
            })

        # Use async_to_sync to send the notification (now as an array)
        async_to_sync(channel_layer.group_send)(
            "pmissions_group", {
                "type": "pmission_update",
                "pmissions": json.dumps(notification_data)  # Send the array of missions
            }
        )

class SMission(models.Model):
    mmission = models.ForeignKey(MMission, on_delete=models.CASCADE, null=True)
    car_type = models.CharField(null=True, max_length=50)
    car_mark = models.CharField(null=True, max_length=50)
    car_num = models.CharField(null=True, blank=True, max_length=50)
    car_color = models.CharField(null=True, blank=True, max_length=50)
    receipt = models.CharField(null=True, blank=True, max_length=20, default="Assigned")
    created_by = models.CharField(blank=True, null=True, max_length=50)
    created_at = models.DateTimeField(default=datetime.now)
    def __str__(self):
        return str(self.mmission.id)

