from django.contrib import admin
from .models import Drivers, Treasury, MMission, SMission, PMission

# Register your models here.
admin.site.register(Drivers)
admin.site.register(Treasury)
admin.site.register(MMission)
admin.site.register(SMission)
admin.site.register(PMission)

