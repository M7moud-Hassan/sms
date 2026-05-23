from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
import qrcode
from io import BytesIO
from django.core.files import File
from datetime import timedelta

from drivers.models import Drivers

class CategoryCard(models.Model):
    name = models.CharField(max_length=100)  # e.g., "SMT ELITE", "SMT PREMIUM"
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # card price

    def __str__(self):
        return self.name

class Service(models.Model):
    LOCATION_CHOICES = [
        (1, 'Single Location'),
        (2, 'Pickup and Dropoff'),
    ]
    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.ForeignKey(CategoryCard, on_delete=models.CASCADE, related_name='services')
    location_type = models.IntegerField(choices=LOCATION_CHOICES, default=1)
    # No price – card price is in CategoryCard

    def __str__(self):
        return self.name

class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = PhoneNumberField(unique=True, null=True, blank=True,region='JO')
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Card(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='cards')
    number_card = models.CharField(max_length=20, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    end_at = models.DateTimeField(null=True, blank=True)
    vehicle_number = models.CharField(max_length=20, null=True, blank=True)
    chassis_number = models.CharField(max_length=50, null=True, blank=True)
    qr_code = models.ImageField(upload_to="cards/qr/", blank=True, null=True)
    category = models.ForeignKey(CategoryCard, on_delete=models.SET_NULL, null=True, blank=True, related_name='cards')
    is_active = models.BooleanField(default=True)

    def generate_card_number(self):
        year = timezone.now().year
        last_card = Card.objects.filter(number_card__startswith=f"C-{year}").order_by("-id").first()
        if last_card:
            last_number = int(last_card.number_card.split("-")[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        return f"C-{year}-{new_number:06d}"

    def save(self, *args, **kwargs):
        if not self.number_card:
            self.number_card = self.generate_card_number()
        if not self.end_at:
            self.end_at = timezone.now() + timedelta(days=365*2)
        if not self.qr_code:
            data = f"""
Card Number: {self.number_card}
Customer: {self.customer.name}
Phone: {self.customer.phone}
Chassis: {self.chassis_number}
Vehicle: {self.vehicle_number}
Valid until: {self.end_at.strftime('%Y-%m-%d') if self.end_at else 'N/A'}
            """
            qr = qrcode.make(data.strip())
            buffer = BytesIO()
            qr.save(buffer, format='PNG')
            file_name = f'card_{self.number_card}.png'
            self.qr_code.save(file_name, File(buffer), save=False)
        super().save(*args, **kwargs)

    def deactivate(self):
        self.is_active = False
        self.save()

    def activate(self):
        self.is_active = True
        self.save()

    def __str__(self):
        return f"{self.number_card} - {self.customer.name}"

class ServiceQuota(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='service_quotas')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='card_quotas')
    remaining_uses = models.PositiveIntegerField(default=0)
    total_provided = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('card', 'service')

    def __str__(self):
        return f"{self.card.number_card} - {self.service.name}: {self.remaining_uses} left"

class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('inprogress', 'In Progress'),      # NEW
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]
    request_number = models.CharField(max_length=20, unique=True, blank=True)
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='service_requests')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='requests')
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    from_location = models.CharField(max_length=255, blank=True, null=True)
    to_location = models.CharField(max_length=255, blank=True, null=True)
    contact_phone = PhoneNumberField(blank=True, null=True,region='JO')

    def generate_request_number(self):
        year = timezone.now().year
        last_req = ServiceRequest.objects.filter(request_number__startswith=f"REQ-{year}").order_by("-id").first()
        if last_req:
            last_number = int(last_req.request_number.split("-")[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        return f"REQ-{year}-{new_number:06d}"

    def save(self, *args, **kwargs):
        if not self.request_number:
            self.request_number = self.generate_request_number()
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.request_number} - {self.card.number_card} - {self.service.name}"

class RequsetMission(models.Model):
    description = models.CharField(blank=True, null=True, max_length=50)
    driver = models.ForeignKey(Drivers, on_delete=models.CASCADE, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)  # NEW
    date = models.DateField(null=True, blank=True)
    from_location = models.CharField(null=True, blank=True, max_length=50)
    to_location = models.CharField(null=True, blank=True, max_length=50)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    notes = models.CharField(blank=True, null=True, max_length=500)
    receipt = models.CharField(null=True, blank=True, max_length=20)
    scost = models.CharField(null=True, blank=True, max_length=100)
    count = models.IntegerField(null=True, blank=True, default=0)
    accept = models.CharField(null=True, blank=True, max_length=20)
    created_by = models.CharField(blank=True, null=True, max_length=50)
    created_at = models.DateTimeField(default=timezone.now)
    contact_phone = PhoneNumberField(blank=True, null=True,region='JO')
    service_request = models.OneToOneField(
        ServiceRequest,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='mission'
    )

    def __str__(self):
        return str(self.id)
    
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

class UserLastSeen(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='last_seen')
    last_request_time = models.DateTimeField(default=timezone.now)