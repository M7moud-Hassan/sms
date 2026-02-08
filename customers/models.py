from django.db import models
from datetime import datetime
#from invoices.models import Invoices

# Create your models here.
class Customers(models.Model):
    name = models.CharField(null=True, max_length=200)
    address = models.CharField(null=True, blank=True, max_length=500)
    phone = models.CharField(unique=True, null=True, max_length=30)
    mail = models.CharField(null=True, blank=True, max_length=50)
    logo = models.ImageField(blank=True, null=True, upload_to='customer_logos/')
    payment = models.CharField(null=True, max_length=10, default="نقدي")
    balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    notes = models.CharField(null=True, blank=True, max_length=500)
    username = models.CharField(null=True, blank=True, max_length=20)
    password = models.CharField(null=True, blank=True, max_length=20)
    created_by = models.CharField(blank=True, null=True, max_length=50)
    created_at = models.DateTimeField(default=datetime.now)
    def __str__(self):
        return self.name

class Papers(models.Model):
    customer = models.ForeignKey(Customers, on_delete=models.CASCADE, null=True)
    description = models.CharField(null=True, max_length=200)
    paper = models.FileField(upload_to='customer_pdfs/', null=True, blank=True)  # Add this line
    def __str__(self):
        return self.description

class Treasury(models.Model):
    customer = models.ForeignKey(Customers, on_delete=models.CASCADE, null=True)
    invoice = models.ForeignKey('invoices.Invoices', on_delete=models.CASCADE, null=True, related_name='customer_treasury')
    number = models.IntegerField(unique=True, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    payment = models.CharField(null=True, max_length=10)
    created_by = models.CharField(blank=True, null=True, max_length=50)
    created_at = models.DateTimeField(default=datetime.now)
    def __str__(self):
        return str(self.customer)

class Customer_Vehicles(models.Model):
    customer = models.ForeignKey(Customers, on_delete=models.CASCADE, null=True)
    car_type = models.CharField(null=True, max_length=50)
    car_mark = models.CharField(null=True, max_length=50)
    car_num = models.CharField(null=True, blank=True, max_length=50)
    car_color = models.CharField(null=True, blank=True, max_length=50)
    def __str__(self):
        return self.customer.name
