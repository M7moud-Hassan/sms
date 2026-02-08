from django.contrib import admin
from .models import Supplier, Treasury, MainItems, Invoices, Items, Papers

# Register your models here.
admin.site.register(Supplier)
admin.site.register(Treasury)
admin.site.register(MainItems)
admin.site.register(Invoices)
admin.site.register(Items)
admin.site.register(Papers)

