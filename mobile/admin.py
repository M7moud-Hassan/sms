from django.contrib import admin
from .models import Used_Vehicle, Auto_Oil, Fuel_Filling, Logs

# Register your models here.
admin.site.register(Used_Vehicle)
admin.site.register(Auto_Oil)
admin.site.register(Fuel_Filling)
admin.site.register(Logs)
