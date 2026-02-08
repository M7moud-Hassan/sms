from django.contrib import admin
from .models import Customers, Papers, Treasury

# Register your models here.
admin.site.register(Customers)
admin.site.register(Papers)
admin.site.register(Treasury)
