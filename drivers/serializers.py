from rest_framework import serializers
from .models import Drivers, Treasury

class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drivers
        fields = '__all__'

class TreasurySerializer(serializers.ModelSerializer):
    class Meta:
        model = Treasury
        fields = '__all__'

