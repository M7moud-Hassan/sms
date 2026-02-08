from rest_framework import serializers
from .models import Used_Vehicle, Auto_Oil, Fuel_Filling, Logs
from customers.models import Customers
from recipt_vouchers.models import Vouchers, Attachments
from invoices.models import Invoices, Items
from drivers.models import MMission, SMission

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Used_Vehicle
        fields = ['vehicle_number']

class LogsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Logs
        fields = ['username', 'password', 'vehicle_number']

class CustomersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customers
        fields = ['name', 'phone', 'mail', 'logo']

class Vouchers1Serializer(serializers.ModelSerializer):
    class Meta:
        model = Vouchers
        fields = ['number', 'car_type', 'car_num', 'car_mark', 'car_color', 'car_owner', 'driver_name']

class Vouchers2Serializer(serializers.ModelSerializer):
    class Meta:
        model = Vouchers
        fields = ['strike_chart', 'recipient_from_name', 'receipt_from_signature', 'receipt_from_location', 'notes']

class AttachmentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachments
        fields = '__all__'

class Vouchers3Serializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    owner_phone = serializers.SerializerMethodField()
    class Meta:
        model = Vouchers
        fields = ['number', 'car_type', 'car_num', 'owner_name', 'owner_phone', 'driver_name']
    def get_owner_name(self, obj):
        return obj.car_owner.name
    def get_owner_phone(self, obj):
        return obj.car_owner.phone

class Vouchers31Serializer(serializers.ModelSerializer):
    class Meta:
        model = Vouchers
        fields = ['strike_chart', 'recipient_from_name', 'receipt_from_signature', 'receipt_from_location', 'receipt_from_time', 'notes', 'recipient_to_name', 'receipt_to_signature', 'receipt_to_location', 'receipt_to_time']

class Vouchers32Serializer(serializers.ModelSerializer):
    class Meta:
        model = Vouchers
        fields = ['strike_chart', 'recipient_to_name', 'receipt_to_signature', 'receipt_to_location', 'notes']

class Vouchers41Serializer(serializers.ModelSerializer):
    class Meta:
        model = Vouchers
        fields = ['car_type', 'receipt_from_location', 'receipt_to_location']

class InvoicesSerializer(serializers.ModelSerializer):
    driver_name = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    used_vehicle = serializers.SerializerMethodField()
    class Meta:
        model = Invoices
        fields = ['id', 'driver_name', 'number', 'type', 'date', 'customer_name', 'dinar', 'fils', 'tamount', 'samount', 'car', 'notes', 'created_at', 'used_vehicle']
    def get_driver_name(self, obj):
        return obj.driver.name
    def get_customer_name(self, obj):
        return obj.require_id.name
    def get_used_vehicle(self, obj):
        return obj.vehicle.vehicle_number

class ItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Items
        fields = '__all__'

class Items1Serializer(serializers.ModelSerializer):
    class Meta:
        model = Items
        fields = ['udinar', 'ufils', 'qty', 'description']

class Items2Serializer(serializers.ModelSerializer):
    class Meta:
        model = Items
        fields = ['udinar', 'ufils', 'qty', 'description', 'number']

class InvoicesSerializer2(serializers.ModelSerializer):
    class Meta:
        model = Invoices
        fields = ['type', 'notes']

class MMissionSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    class Meta:
        model = MMission
        fields = ['id', 'customer_name', 'customer_phone', 'date', 'count', 'from_location', 'to_location', 'cost', 'notes']
    def get_customer_name(self, obj):
        return obj.customer.name
    def get_customer_phone(self, obj):
        return obj.customer.phone

class SMissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMission
        fields = ['car_type', 'car_mark', 'car_num', 'car_color']

class OilSerializer1(serializers.ModelSerializer):
    class Meta:
        model = Auto_Oil
        fields = '__all__'

class OilSerializer2(serializers.ModelSerializer):
    vehicle_number = serializers.SerializerMethodField()
    class Meta:
        model = Auto_Oil
        fields = ['vehicle_number', 'vehicle_meter', 'maintenance_center', 'air_filter', 'diesel_filter', 'notes', 'meter_image']
    def get_vehicle_number(self, obj):
        return obj.vehicle.vehicle_number

class FuelSerializer1(serializers.ModelSerializer):
    class Meta:
        model = Fuel_Filling
        fields = '__all__'

class FuelSerializer2(serializers.ModelSerializer):
    vehicle_number = serializers.SerializerMethodField()
    class Meta:
        model = Fuel_Filling
        fields = ['vehicle_number', 'vehicle_meter', 'litres', 'amount', 'location', 'notes', 'meter_image']
    def get_vehicle_number(self, obj):
        return obj.vehicle.vehicle_number