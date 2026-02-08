from django.contrib import admin
from .models import Invoices, Items, FotarahResponses

# Register your models here.
admin.site.register(Invoices)
admin.site.register(Items)
admin.site.register(FotarahResponses)
