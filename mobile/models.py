from django.db import models
from datetime import datetime
from drivers.models import Drivers

# Create your models here.
class Used_Vehicle(models.Model):
    vehicle_number = models.CharField(unique=True, blank=True, null=True, max_length=200)
    image = models.ImageField(blank=True, null=True, upload_to='vehicles/')
    type = models.CharField(null=True, blank=True, max_length=50)
    date = models.DateField(null=True, blank=True)
    income = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    expenses = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    status = models.CharField(null=True, blank=True, max_length=20)
    driver = models.CharField(null=True, blank=True, max_length=50)
    default_oil_diff = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    default_fuel_filter_diff = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    default_air_filter_diff = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    fuel_meter = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    oil_meter = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    fuel_filter_meter = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    air_filter_meter = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    current_oil_diff = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    current_fuel_filter_diff = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    current_air_filter_diff = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    notes = models.CharField(blank=True, null=True, max_length=500)
    created_by = models.CharField(blank=True, null=True, max_length=50)
    created_at = models.DateTimeField(default=datetime.now)
    def __str__(self):
        return self.vehicle_number

class Auto_Oil(models.Model):
    vehicle = models.ForeignKey(Used_Vehicle, on_delete=models.CASCADE, null=True)
    driver = models.ForeignKey(Drivers, on_delete=models.CASCADE, null=True)
    vehicle_meter = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    maintenance_center = models.CharField(null=True, blank=True, max_length=100)
    air_filter = models.BooleanField(null=True)
    diesel_filter = models.BooleanField(null=True)
    notes = models.CharField(null=True, blank=True, max_length=500)
    meter_image = models.ImageField(blank=True, null=True, upload_to='oil/')
    created_at = models.DateTimeField(default=datetime.now)
    def __str__(self):
        return self.vehicle.vehicle_number

class Fuel_Filling(models.Model):
    vehicle = models.ForeignKey(Used_Vehicle, on_delete=models.CASCADE, null=True)
    driver = models.ForeignKey(Drivers, on_delete=models.CASCADE, null=True)
    vehicle_meter = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    litres = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    location = models.CharField(null=True, blank=True, max_length=200)
    notes = models.CharField(null=True, blank=True, max_length=500)
    meter_image = models.ImageField(blank=True, null=True, upload_to='fuel/')
    created_at = models.DateTimeField(default=datetime.now)
    def __str__(self):
        return self.vehicle.vehicle_number

class Logs(models.Model):
    username = models.CharField(null=True, max_length=20)
    password = models.CharField(null=True, max_length=20)
    vehicle_number = models.CharField(null=True, max_length=200)
    created_at = models.DateTimeField(default=datetime.now)
    def __str__(self):
        return self.username
