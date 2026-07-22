from django.db import models
from django.db.models import Sum
from django.conf import settings
from django.urls import reverse
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from io import BytesIO
from django.core.files import File
from datetime import timedelta
import uuid

from drivers.models import Drivers

class CategoryCard(models.Model):
    name = models.CharField(max_length=100)  # e.g., "SMT ELITE", "SMT PREMIUM"
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # card price
    default_quota = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.name

class Showroom(models.Model):
    """A car dealership that gifts cards to its own customers. A card with no showroom is an individual card."""
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ['name']

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
    default_quota = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Overrides the category's default quota for this specific service when issuing a new card. Leave blank to use the category default."
    )

    def __str__(self):
        return self.name

class Customer(models.Model):
    PAYMENT_CASH = 'cash'
    PAYMENT_CREDIT = 'credit'
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, 'Cash'),
        (PAYMENT_CREDIT, 'Credit'),
    ]

    name = models.CharField(max_length=100)
    phone = PhoneNumberField(unique=True, null=True, blank=True,region='JO')
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='cardholders/logos/', blank=True, null=True)
    payment = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default=PAYMENT_CASH)
    notes = models.CharField(max_length=500, blank=True, null=True)

    def __str__(self):
        return self.name

    @property
    def unpaid_cards_total(self):
        """Sum of category prices for this cardholder's not-yet-paid cards (Python-side sum,
        so callers that already prefetched `cards__category` don't trigger extra queries)."""
        return sum((c.category.price if c.category else 0) for c in self.cards.all() if not c.is_paid)

    @property
    def unpaid_invoices_total(self):
        return ServiceInvoice.objects.filter(
            service_request__card__customer=self, status='unpaid'
        ).aggregate(total=Sum('amount'))['total'] or 0

    @property
    def balance(self):
        """Auto-calculated outstanding balance: unpaid card prices + unpaid service-overage
        invoices. Not a stored field, so it can't drift from what's actually marked paid."""
        return self.unpaid_cards_total + self.unpaid_invoices_total

class Card(models.Model):
    # Public identifier used in the QR scan link, so card IDs can't be guessed/enumerated (e.g. /scan/1/, /scan/2/...).
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='cards')
    number_card = models.CharField(max_length=20, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    end_at = models.DateTimeField(null=True, blank=True)
    vehicle_number = models.CharField(max_length=20, null=True, blank=True)
    chassis_number = models.CharField(max_length=50, null=True, blank=True)
    type_car = models.CharField(max_length=100, null=True, blank=True)
    color_car = models.CharField(max_length=50, null=True, blank=True)
    qr_code = models.ImageField(upload_to="cards/qr/", blank=True, null=True)
    category = models.ForeignKey(CategoryCard, on_delete=models.SET_NULL, null=True, blank=True, related_name='cards')
    showroom = models.ForeignKey(Showroom, on_delete=models.SET_NULL, null=True, blank=True, related_name='cards', help_text="Leave blank for an individual card")
    is_active = models.BooleanField(default=True)
    is_paid = models.BooleanField(default=False, help_text="Whether the card price has been paid")
    paid_at = models.DateTimeField(null=True, blank=True)

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
            # self.uuid is already set (default=uuid.uuid4 applies at instantiation), so the
            # scan URL can be built and the QR generated before the first insert.
            scan_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}{reverse('card_scan', kwargs={'card_uuid': self.uuid})}"
            qr = qrcode.QRCode(
                version=None,
                error_correction=ERROR_CORRECT_H,  # high redundancy: survives print wear/scratches
                box_size=12,                       # higher-res source image, sharper when scaled on the printed card
                border=4,
            )
            qr.add_data(scan_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
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
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_accuracy = models.FloatField(null=True, blank=True, help_text="GPS accuracy in meters, as reported by the customer's device")

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

class ServiceInvoice(models.Model):
    """Bill for an additional cost incurred on a service request's mission (e.g. towing beyond
    what was covered, extra fuel, etc). Sourced from RequsetMission.cost + cost_reason. Not
    related to the separate `invoices` app, which handles a different, driver/customer-facing
    dinar billing flow."""
    STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('cliq', 'CliQ'),
        ('bank_transfer', 'Bank Transfer'),
        ('card', 'Card'),
    ]
    invoice_number = models.CharField(max_length=20, unique=True, blank=True)
    service_request = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE, related_name='invoice')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def generate_invoice_number(self):
        year = timezone.now().year
        last_inv = ServiceInvoice.objects.filter(invoice_number__startswith=f"INV-{year}").order_by("-id").first()
        if last_inv:
            last_number = int(last_inv.invoice_number.split("-")[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        return f"INV-{year}-{new_number:06d}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        super().save(*args, **kwargs)

    @classmethod
    def sync_for_mission(cls, mission):
        """Recompute (or remove) the invoice for a mission's service request based on its
        current cost/cost_reason. Never touches status/paid_at on an existing invoice, so
        recalculating the amount can't silently un-pay one."""
        service_request = mission.service_request
        if service_request is None or not mission.cost or mission.cost <= 0:
            if service_request is not None:
                cls.objects.filter(service_request=service_request).delete()
            return None

        invoice, _ = cls.objects.update_or_create(
            service_request=service_request,
            defaults={
                'amount': mission.cost,
                'reason': mission.cost_reason or '',
            }
        )
        return invoice

    def __str__(self):
        return f"{self.invoice_number} - {self.service_request.card.number_card} - {self.amount}"

class RequsetMission(models.Model):
    description = models.CharField(blank=True, null=True, max_length=50)
    driver = models.ForeignKey(Drivers, on_delete=models.CASCADE, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)  # NEW
    date = models.DateTimeField(null=True, blank=True)
    from_location = models.CharField(null=True, blank=True, max_length=50)
    to_location = models.CharField(null=True, blank=True, max_length=50)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    cost_reason = models.CharField(blank=True, null=True, max_length=255, help_text="Reason for the additional cost, e.g. 'towing beyond included distance'")
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

class FCMToken(models.Model):
    """A registered Firebase Cloud Messaging web-push token.
    Staff tokens are tied to a logged-in User (notified on new service requests).
    Customer tokens are tied to the specific ServiceRequest they submitted, since
    customers never log in (notified when a mission/driver is assigned to it)."""
    token = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name='fcm_tokens')
    service_request = models.ForeignKey(ServiceRequest, null=True, blank=True, on_delete=models.CASCADE, related_name='fcm_tokens')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FCMToken(user={self.user_id}, request={self.service_request_id})"