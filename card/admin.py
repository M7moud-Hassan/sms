from django.contrib import admin

from card.models import ServiceRequest, ServiceQuota, Card, Service, Showroom, FCMToken

# Register your models here.

@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'card', 'customer_name', 'contact_phone',
                    'service', 'status', 'requested_at')
    list_filter = ('status', 'service')
    search_fields = ('request_number', 'card__number_card', 'card__customer__name', 'contact_phone')
    readonly_fields = ('requested_at', 'latitude', 'longitude', 'location_accuracy')

    @admin.display(description='Cardholder', ordering='card__customer__name')
    def customer_name(self, obj):
        return obj.card.customer.name


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