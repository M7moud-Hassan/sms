from django.db import models
from datetime import datetime
from django.utils import timezone
from invoices.models import Invoices
from customers.models import Customers

# Create your models here.
class Vouchers(models.Model):
    number = models.IntegerField(unique=True, null=True)
    car_type = models.CharField(null=True, max_length=50)
    car_num = models.CharField(null=True, blank=True, max_length=50)
    car_mark = models.CharField(null=True, blank=True, max_length=50)
    car_color = models.CharField(null=True, blank=True, max_length=50)
    car_owner = models.ForeignKey(Customers, on_delete=models.CASCADE, null=True)
    strike_chart = models.ImageField(null=True, blank=True, upload_to='recipt_strike/')
    recipient_from_name = models.CharField(null=True, blank=True, max_length=50)
    receipt_from_signature = models.ImageField(null=True, blank=True, upload_to='receipt_from_signatures/')
    receipt_from_location = models.CharField(null=True, blank=True, max_length=500)
    receipt_from_time = models.DateTimeField(blank=True, null=True)
    recipient_to_name = models.CharField(null=True, blank=True, max_length=50)
    receipt_to_signature = models.ImageField(null=True, blank=True, upload_to='receipt_to_signatures/')
    receipt_to_location = models.CharField(null=True, blank=True, max_length=500)
    receipt_to_time = models.DateTimeField(blank=True, null=True)
    notes = models.CharField(null=True, blank=True, max_length=500)
    driver_name = models.CharField(blank=True, null=True, max_length=50)
    invoice = models.ForeignKey(Invoices, on_delete=models.CASCADE, null=True, blank=True)
    def __str__(self):
        return str(self.car_num)

class Attachments(models.Model):
    voucher = models.ForeignKey(Vouchers, on_delete=models.CASCADE, null=True)
    strike_chart = models.ImageField(null=True, blank=True, upload_to='recipt_att/')
    page = models.CharField(null=True, blank=True, max_length=50)
    def __str__(self):
        return str(self.voucher.id)
