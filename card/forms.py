from django import forms

from drivers.models import Drivers
from .models import Customer, Card, CategoryCard, RequsetMission, Service, ServiceQuota, ServiceRequest
from django.forms import inlineformset_factory
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
        fields = ['customer', 'category', 'vehicle_number', 'chassis_number', 'end_at', 'is_active']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select', 'data-category-id': ''}),
            'vehicle_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABC-123'}),
            'chassis_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Chassis #'}),
            'end_at': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.all().order_by('name')
        self.fields['category'].queryset = CategoryCard.objects.all().order_by('name')
        self.fields['end_at'].required = False
        self.fields['is_active'].label = "Active card"
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
        fields = ['name', 'description', 'price']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'description', 'location_type', 'category']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        'location_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
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
        fields = ['service', 'notes', 'from_location', 'to_location','contact_phone']  # أضفنا الحقلين
        widgets = {
            'service': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'from_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pickup location'}),
            'to_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dropoff location'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter contact phone number'}),
        }

    def __init__(self, *args, **kwargs):
        self.card = kwargs.pop('card', None)
        super().__init__(*args, **kwargs)
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
    class Meta:
        model = RequsetMission
        fields = [
            'driver', 'date', 'from_location', 'to_location',
            'cost', 'notes', 'receipt', 'scost', 'count', 'accept'
        ]
        widgets = {
            'driver': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'from_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pickup'}),
            'to_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dropoff'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
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