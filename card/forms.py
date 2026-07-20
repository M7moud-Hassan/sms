from django import forms
from django.core.exceptions import ValidationError
import re

from drivers.models import Drivers
from .models import Customer, Card, CategoryCard, RequsetMission, Service, ServiceQuota, ServiceRequest, Showroom
from django.forms import inlineformset_factory

VIN_RE = re.compile(r'^[0-9A-HJ-NPR-Z]{17}$')

def validate_vin(value):
    if value and not VIN_RE.match(value.upper()):
        raise ValidationError(
            'VIN must be exactly 17 characters using digits 0–9 and uppercase letters A–Z '
            'excluding I, O, and Q.'
        )
class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'email', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1234567890'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class CardForm(forms.ModelForm):
    class Meta:
        model = Card
        fields = ['customer', 'category', 'showroom', 'vehicle_number', 'chassis_number', 'type_car', 'color_car', 'end_at', 'is_active']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select', 'data-category-id': ''}),
            'showroom': forms.Select(attrs={'class': 'form-select'}),
            'vehicle_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABC-123'}),
            'chassis_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '17-character VIN',
                'maxlength': '17',
                'minlength': '17',
                'pattern': '[0-9A-HJ-NPR-Z]{17}',
                'title': '17 characters: digits 0–9 and letters A–Z except I, O, Q',
                'oninput': 'this.value=this.value.toUpperCase()',
            }),
            'type_car': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Toyota Camry'}),
            'color_car': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. White'}),
            'end_at': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.all().order_by('name')
        self.fields['category'].queryset = CategoryCard.objects.all().order_by('name')
        self.fields['showroom'].queryset = Showroom.objects.all().order_by('name')
        self.fields['showroom'].required = False
        self.fields['showroom'].empty_label = "-- None (Individual card) --"
        self.fields['end_at'].required = False
        self.fields['is_active'].label = "Active card"
        self.fields['chassis_number'].validators.append(validate_vin)
        self.fields['chassis_number'].required = False

class ShowroomForm(forms.ModelForm):
    class Meta:
        model = Showroom
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Showroom name'}),
        }
ServiceQuotaFormSet = inlineformset_factory(
    Card,
    ServiceQuota,
    fields=('service', 'remaining_uses'),          # removed expiration_date
    extra=3,
    can_delete=True,
    widgets={
        'service': forms.Select(attrs={'class': 'form-select service-select'}),
        'remaining_uses': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'value': 0}),
    },
    labels={
        'remaining_uses': 'Initial Quota',
    }
)

class CategoryForm(forms.ModelForm):
    class Meta:
        model = CategoryCard
        fields = ['name', 'description', 'price', 'default_quota']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'default_quota': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'description', 'location_type', 'category', 'default_quota']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'location_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'default_quota': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Uses category default'}),
        }

class BonusQuotaForm(forms.ModelForm):
    class Meta:
        model = ServiceQuota
        fields = ['service', 'remaining_uses']
        widgets = {
            'service': forms.Select(attrs={'class': 'form-select'}),
            'remaining_uses': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
        labels = {
            'remaining_uses': 'Bonus Quantity',
        }

    def __init__(self, *args, **kwargs):
        self.card = kwargs.pop('card', None)
        super().__init__(*args, **kwargs)
        # Only show services not already having a quota for this card? Or allow adding more.
        self.fields['service'].queryset = Service.objects.all().order_by('name')

class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ['service', 'notes', 'from_location', 'to_location', 'contact_phone',
                  'latitude', 'longitude', 'location_accuracy']  # أضفنا الحقلين + موقع العميل
        widgets = {
            'service': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'from_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pickup location'}),
            'to_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dropoff location'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter contact phone number'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'location_accuracy': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.card = kwargs.pop('card', None)
        super().__init__(*args, **kwargs)
        self.fields['latitude'].required = False
        self.fields['longitude'].required = False
        self.fields['location_accuracy'].required = False
        if self.card:
            # تقتصر الخدمات على تلك التي لها رصيد > 0 لهذه البطاقة
            self.fields['service'].queryset = Service.objects.filter(
                card_quotas__card=self.card,
                card_quotas__remaining_uses__gt=0
            ).distinct()
            self.fields['service'].empty_label = "-- Select a service --"
class RequestStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ['status', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class MissionForm(forms.ModelForm):
    date = forms.DateTimeField(
        required=False,
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'],
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
    )

    class Meta:
        model = RequsetMission
        fields = [
            'driver', 'date', 'from_location', 'to_location',
            'cost', 'cost_reason', 'notes', 'receipt', 'scost', 'count', 'accept'
        ]
        widgets = {
            'driver': forms.Select(attrs={'class': 'form-select'}),
            'from_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pickup'}),
            'to_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dropoff'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cost_reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. towing beyond included distance'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'receipt': forms.TextInput(attrs={'class': 'form-control'}),
            'scost': forms.TextInput(attrs={'class': 'form-control'}),
            'count': forms.NumberInput(attrs={'class': 'form-control'}),
            'accept': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['driver'].queryset = Drivers.objects.all().order_by('name')
        self.fields['date'].required = False