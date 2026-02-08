from django.db import models
from datetime import datetime
from customers.models import Customers
from mobile.models import Used_Vehicle
from drivers.models import Drivers

# Create your models here.

class FotarahResponses(models.Model):
    invoice = models.ForeignKey('Invoices', on_delete=models.CASCADE)
    success = models.BooleanField()
    message = models.TextField()
    fotarah_invoice_id = models.CharField(max_length=100, null=True, blank=True)
    qr_code_base64 = models.TextField(null=True, blank=True)
    qr_code_binary = models.TextField(null=True, blank=True)
    response_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Response for Invoice {self.invoice.number}"


class Invoices(models.Model):
    driver = models.ForeignKey(Drivers, on_delete=models.CASCADE, null=True)
    number = models.IntegerField(null=True, blank=True)
    type = models.CharField(null=True, max_length=10)
    date = models.DateField(null=True, blank=True)
    require_id = models.ForeignKey(Customers, on_delete=models.CASCADE, null=True, blank=True)
    dinar = models.IntegerField(null=True, blank=True, default=0)
    fils = models.IntegerField(null=True, blank=True, default=0)
    tamount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    samount = models.CharField(max_length=200, null=True, default="فقط وقدره صفر دينار لا غير")
    car = models.CharField(max_length=5000, null=True)
    notes = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    vehicle = models.ForeignKey(Used_Vehicle, on_delete=models.CASCADE, null=True)
    exported = models.CharField(blank=True, null=True, max_length=5)
    driver_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    customer_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    fotarah_sent = models.BooleanField(default=False)
    fotarah_success = models.BooleanField(null=True)

    def __str__(self):
        return str(self.number)


class Items(models.Model):
    number = models.ForeignKey(Invoices, on_delete=models.CASCADE, null=True)
    udinar = models.IntegerField(null=True, blank=True)
    ufils = models.IntegerField(null=True, blank=True)
    qty = models.IntegerField(null=True, blank=True)
    description = models.CharField(max_length=200, null=True)
    adinar = models.IntegerField(null=True, blank=True)
    afils = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return str(self.number)

