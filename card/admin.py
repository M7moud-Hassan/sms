from django.contrib import admin

from card.models import ServiceRequest, ServiceQuota, Card, Service, Showroom, FCMToken

# Register your models here.

admin.site.register(ServiceRequest)


@admin.register(Showroom)
class ShowroomAdmin(admin.ModelAdmin):
    search_fields = ('name',)


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    search_fields = ('number_card', 'customer__name', 'vehicle_number')
    list_filter = ('showroom',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    search_fields = ('name',)


@admin.register(ServiceQuota)
class ServiceQuotaAdmin(admin.ModelAdmin):
    list_display = ('card', 'service', 'remaining_uses', 'total_provided', 'updated_at')
    list_filter = ('service',)
    search_fields = ('card__number_card', 'card__customer__name', 'service__name')
    autocomplete_fields = ('card', 'service')


@admin.register(FCMToken)
class FCMTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'service_request', 'created_at')
    list_filter = ('user',)
    search_fields = ('token', 'user__username', 'service_request__request_number')