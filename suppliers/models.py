from django.db import models
from datetime import datetime
from mobile.models import Used_Vehicle

# Create your models here.
class Supplier(models.Model):
    name = models.CharField(unique=True, null=True, max_length=50)
    phone = models.CharField(unique=True, null=True, max_length=30)
    mail = models.CharField(null=True, blank=True, max_length=50)
    logo = models.ImageField(blank=True, null=True, upload_to='supplier_logos/')
    balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.CharField(null=True, blank=True, max_length=500)
    created_by = models.CharField(blank=True, null=True, max_length=50)
    created_at = models.DateTimeField(default=datetime.now)
    def __str__(self):
        return self.name

class Invoices(models.Model):
    number = models.IntegerField(null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    type = models.CharField(null=True, max_length=10)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, null=True)
    tamount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    samount = models.CharField(max_length=200, null=True, default="فقط وقدره صفر دينار لا غير")
    notes = models.CharField(null=True, blank=True, max_length=200)
    paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    created_at = models.DateTimeField(default=datetime.now)
    created_by = models.CharField(max_length=50, null=True)
    def __str__(self):
        return str(self.number)

class Papers(models.Model):
    invoice = models.ForeignKey(Invoices, on_delete=models.CASCADE, null=True)
    description = models.CharField(null=True, max_length=200)
    paper = models.FileField(upload_to='supplier_pdfs/', null=True, blank=True)  # Add this line
    def __str__(self):
        return str(self.invoice.number)

class Treasury(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, null=True)
    invoice = models.ForeignKey(Invoices, on_delete=models.CASCADE, null=True)
    number = models.IntegerField(unique=True, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    payment = models.CharField(null=True, max_length=10)
    created_by = models.CharField(blank=True, null=True, max_length=50)
    created_at = models.DateTimeField(default=datetime.now)
    def __str__(self):
        return str(self.supplier)

class MainItems(models.Model):
    item = models.CharField(unique=True, null=True, max_length=50)
    def __str__(self):
        return str(self.item)

class Items(models.Model):
    invoice = models.ForeignKey(Invoices, on_delete=models.CASCADE, null=True)
    vehicle = models.ForeignKey(Used_Vehicle, on_delete=models.CASCADE, null=True)
    item = models.CharField(max_length=200, null=True)
    description = models.CharField(max_length=200, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    qty = models.IntegerField(null=True, blank=True)
    tamount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    created_by = models.CharField(blank=True, null=True, max_length=50)
    created_at = models.DateTimeField(default=datetime.now)
    def __str__(self):
        return str(self.invoice)
