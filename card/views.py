from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, Http404
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Sum, F
from django.utils import timezone
from django.contrib import messages

from customers.models import Customers
from drivers.models import Drivers, MMission
from .models import Card, Customer, CategoryCard, RequsetMission, Service, ServiceQuota, ServiceRequest, UserLastSeen
from .forms import BonusQuotaForm, CardForm, CategoryForm, CustomerForm, MissionForm, ServiceForm, ServiceRequestForm, RequestStatusUpdateForm

# ──────────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────────
# class DashboardView(LoginRequiredMixin, ListView):
#     model = Card
#     template_name = 'cards/dashboard.html'
#     context_object_name = 'recent_cards'

#     def get_queryset(self):
#         return Card.objects.select_related('customer', 'category').order_by('-created_at')[:10]

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['total_cards'] = Card.objects.count()
#         context['active_cards'] = Card.objects.filter(is_active=True).count()
#         context['expired_cards'] = Card.objects.filter(end_at__lt=timezone.now()).count()
#         context['total_customers'] = Customer.objects.count()
#         # For modal
#         context['customers'] = Customer.objects.all().order_by('name')
#         context['categories'] = CategoryCard.objects.all().order_by('name')
#         context['active_tab'] ='cards'
#         return context

class DashboardView(LoginRequiredMixin, ListView):
    model = Card
    template_name = 'cards/dashboard.html'
    context_object_name = 'recent_cards'

    def get_queryset(self):
        return Card.objects.select_related('customer', 'category').order_by('-created_at')[:10]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        thirty_days_later = today + timedelta(days=30)

        # إحصائيات البطاقات
        context['total_cards'] = Card.objects.count()
        context['active_cards'] = Card.objects.filter(is_active=True).count()
        context['expired_cards'] = Card.objects.filter(end_at__lt=today).count()
        context['expiring_soon_cards'] = Card.objects.filter(
            end_at__gte=today,
            end_at__lte=thirty_days_later
        ).count()

        # العملاء والخدمات
        context['total_customers'] = Customer.objects.count()
        context['total_services'] = Service.objects.count()
        context['total_requests'] = ServiceRequest.objects.count()
        context['customers'] = Customer.objects.all().order_by('name')
        context['categories'] = CategoryCard.objects.all().order_by('name')

        # الطلبات التي ليس لها مهمة
        context['requests_without_mission'] = ServiceRequest.objects.filter(mission__isnull=True).select_related('card', 'service')

        # عدد الإشعارات (الطلبات بدون مهمة)
        context['notification_count'] = ServiceRequest.objects.filter(mission__isnull=True).count()
        context['active_tab'] ='cards'
        # بيانات للتقارير (يمكن تمريرها إذا لزم)
        return context

# ──────────────────────────────────────────────
# CUSTOMER CRUD (AJAX MODALS)
# ──────────────────────────────────────────────
class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'cards/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '')
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) |
                Q(phone__icontains=q) |
                Q(email__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query_params'] = self.request.GET.copy()
        if 'page' in context['query_params']:
            del context['query_params']['page']
        context['active_tab'] ='cards'
        
        return context

class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'cards/includes/add_customer_modal.html'  # only used for AJAX

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'customer_id': self.object.pk, 'customer_name': self.object.name})
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors})
        return super().form_invalid(form)

class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'cards/includes/edit_customer_modal.html'

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors})
        return super().form_invalid(form)

class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    model = Customer
    template_name = 'cards/includes/delete_customer_modal.html'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return JsonResponse({'success': True})   # fallback

# ──────────────────────────────────────────────
# CARD CRUD (AJAX MODALS)
# ──────────────────────────────────────────────
class CardListView(LoginRequiredMixin, ListView):
    model = Card
    template_name = 'cards/card_list.html'
    context_object_name = 'cards'
    paginate_by = 20
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '')
        if q:
            queryset = queryset.filter(
                Q(number_card__icontains=q) |
                Q(customer__name__icontains=q) |
                Q(vehicle_number__icontains=q)
            )
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query_params'] = self.request.GET.copy()
        if 'page' in context['query_params']:
            del context['query_params']['page']
        context['customers'] = Customer.objects.all().order_by('name')
        context['categories'] = CategoryCard.objects.all().order_by('name')
        context['services'] = Service.objects.all().order_by('name')
        context['active_tab'] ='cards'

        return context

from django.shortcuts import get_object_or_404
from django.views.generic.edit import CreateView, UpdateView
from .models import Card, Customer, CategoryCard, Service, ServiceQuota
from .forms import CardForm

class CardCreateView(LoginRequiredMixin, CreateView):
    model = Card
    form_class = CardForm
    template_name = 'cards/card_form_with_quota.html'
    success_url = reverse_lazy('card_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.all().order_by('name')
        context['categories'] = CategoryCard.objects.all().order_by('name')
        context['active_tab'] ='cards'

        return context

    def form_valid(self, form):
        response = super().form_valid(form)  # saves the card
        service_ids = self.request.POST.getlist('service_id[]')
        quota_values = self.request.POST.getlist('quota[]')
        is_superuser = self.request.user.is_superuser
        category_default = self.object.category.default_quota if self.object.category else 1
        for service_id, quota in zip(service_ids, quota_values):
            quota_int = int(quota) if is_superuser else category_default
            ServiceQuota.objects.update_or_create(
                card=self.object,
                service_id=service_id,
                defaults={'remaining_uses': quota_int, 'total_provided': quota_int}
            )
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return response

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors})
        return super().form_invalid(form)


class CardUpdateView(LoginRequiredMixin, UpdateView):
    model = Card
    form_class = CardForm
    template_name = 'cards/card_form_with_quota.html'
    success_url = reverse_lazy('card_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.all().order_by('name')
        context['categories'] = CategoryCard.objects.all().order_by('name')
        context['existing_quotas'] = self.object.service_quotas.all()
        context['active_tab'] ='cards'

        return context

    def form_valid(self, form):
        # Save the card first
        self.object = form.save()

        # Process service quotas
        existing = {q.service_id: q for q in self.object.service_quotas.all()}
        service_ids = self.request.POST.getlist('service_id[]')
        quota_values = self.request.POST.getlist('quota[]')

        for service_id, quota in zip(service_ids, quota_values):
            quota = int(quota)
            if quota > 0:
                if int(service_id) in existing:
                    q = existing[int(service_id)]
                    q.remaining_uses = quota
                    q.total_provided = quota
                    q.save()
                else:
                    ServiceQuota.objects.create(
                        card=self.object,
                        service_id=service_id,
                        remaining_uses=quota,
                        total_provided=quota
                    )
            else:
                if int(service_id) in existing:
                    existing[int(service_id)].delete()

        # Respond appropriately for AJAX
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect(self.success_url)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors})
        return super().form_invalid(form) 
class CardDeleteView(LoginRequiredMixin, DeleteView):
    model = Card
    template_name = 'cards/includes/delete_card_modal.html'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return JsonResponse({'success': True})

class CardDetailView(LoginRequiredMixin, DetailView):
    model = Card
    template_name = 'cards/card_detail.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['services'] = Service.objects.all().order_by('name')
        context['customers'] = Customer.objects.all().order_by('name')   # for edit modal
        context['categories'] = CategoryCard.objects.all().order_by('name') # for edit modal
        context['active_tab'] ='cards'
        context['all_services'] = Service.objects.select_related('category').order_by('category__name', 'name')

        return context
    
    


def print_card(request, pk):
    card = get_object_or_404(Card, pk=pk)
    return render(request, 'cards/card_print.html', {'card': card})

# ──────────────────────────────────────────────
# CATEGORY & SERVICE CRUD (AJAX MODALS)
# ──────────────────────────────────────────────
class CategoryServiceView(LoginRequiredMixin, TemplateView):
    template_name = 'cards/category_service.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = CategoryCard.objects.prefetch_related('services').all()
        context['active_tab'] ='cards'

        return context

class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = CategoryCard
    form_class = CategoryForm
    template_name = 'cards/includes/add_category_modal.html'

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors})
        return super().form_invalid(form)

class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = CategoryCard
    form_class = CategoryForm
    template_name = 'cards/includes/edit_category_modal.html'

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors})
        return super().form_invalid(form)


def card_requests(request, pk):
    card = get_object_or_404(Card, pk=pk)
    requests = ServiceRequest.objects.filter(card=card).select_related('service').order_by('-requested_at')
    return render(request, 'cards/card_requests.html', {'card': card, 'requests': requests})

class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = CategoryCard
    template_name = 'cards/includes/delete_category_modal.html'
    success_url = reverse_lazy('category_service')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return JsonResponse({'success': True})

class ServiceCreateView(LoginRequiredMixin, CreateView):
    model = Service
    form_class = ServiceForm
    template_name = 'cards/includes/add_service_modal.html'

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors})
        return super().form_invalid(form)

class ServiceUpdateView(LoginRequiredMixin, UpdateView):
    model = Service
    form_class = ServiceForm
    template_name = 'cards/includes/edit_service_modal.html'

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors})
        return super().form_invalid(form)

class ServiceDeleteView(LoginRequiredMixin, DeleteView):
    model = Service
    template_name = 'cards/includes/delete_service_modal.html'
    success_url = reverse_lazy('category_service')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return JsonResponse({'success': True})
    


class CardScanView(TemplateView):
    """Public page: scan QR code -> show card details and available services."""
    template_name = 'cards/card_scan.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        card_id = self.kwargs.get('pk')
        card = get_object_or_404(Card, pk=card_id, is_active=True)
        context['card'] = card
        # Get services with remaining quota > 0
        quotas = ServiceQuota.objects.filter(card=card, remaining_uses__gt=0).select_related('service')
        context['quotas'] = quotas
        # Form for request
        context['form'] = ServiceRequestForm(card=card)
        context['active_tab'] ='cards'

        return context
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
@method_decorator(csrf_exempt, name='dispatch')
class SubmitServiceRequestView(CreateView):
    model = ServiceRequest
    form_class = ServiceRequestForm
    template_name = 'cards/request_confirmation.html'

    def dispatch(self, request, *args, **kwargs):
        self.card = get_object_or_404(Card, pk=self.kwargs.get('card_id'), is_active=True)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['card'] = self.card
        return kwargs

    def form_valid(self, form):
        form.instance.card = self.card
        self.object = form.save()  # هنا يتم حفظ جميع الحقول بما فيها from_location و to_location
        # إنقاص الرصيد
        try:
            quota = ServiceQuota.objects.get(card=self.card, service=self.object.service)
            if quota.remaining_uses > 0:
                quota.remaining_uses -= 1
                quota.save()
        except ServiceQuota.DoesNotExist:
            pass
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'request_number': self.object.request_number})
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            errors = form.errors.get_json_data()
            return JsonResponse({'success': False, 'errors': errors}, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('request_status', kwargs={'pk': self.object.pk})
class RequestStatusView(DetailView):
    model = ServiceRequest
    template_name = 'cards/request_status.html'
    context_object_name = 'request'

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Card, Service, ServiceQuota, ServiceRequest

class PublicPortalView(TemplateView):
    """Public page for card validation and service requests."""
    template_name = 'cards/public_portal.html'
    
# Public: Validate card by number (returns JSON)
import re
from django.http import JsonResponse
from .models import Card, ServiceQuota

def public_validate_card(request):
    raw_data = request.GET.get('number', '').strip()
    if not raw_data:
        return JsonResponse({'error': 'Card number required'}, status=400)

    if 'Card Number:' in raw_data:
        match = re.search(r'Card Number:\s*(\S+)', raw_data)
        if not match:
            return JsonResponse({'error': 'Invalid QR code format'}, status=400)
        card_number = match.group(1)
    else:
        card_number = raw_data

    try:
        card = Card.objects.select_related('customer').get(number_card=card_number, is_active=True)
    except Card.DoesNotExist:
        return JsonResponse({'error': 'Invalid or inactive card'}, status=404)

    quotas = ServiceQuota.objects.filter(card=card, remaining_uses__gt=0).select_related('service')
    services_data = []
    for q in quotas:
        services_data.append({
            'id': q.service.id,
            'name': q.service.name,
            'remaining': q.remaining_uses,
            'location_type': q.service.location_type,
        })

    data = {
        'id': card.id,
        'number_card': card.number_card,
        'customer': card.customer.name,
        'vehicle': card.vehicle_number or '',
        'valid_until': card.end_at.strftime('%Y-%m-%d') if card.end_at else '',
        'services': services_data,
    }
    return JsonResponse(data)
# Public: Get request status by request number
def public_request_status(request):
    req_number = request.GET.get('number', '').strip()
    if not req_number:
        return JsonResponse({'error': 'Request number required'}, status=400)

    try:
        req = ServiceRequest.objects.select_related('service').get(request_number=req_number)
    except ServiceRequest.DoesNotExist:
        return JsonResponse({'error': 'Request not found'}, status=404)

    status_display = dict(ServiceRequest.STATUS_CHOICES).get(req.status, req.status)

    data = {
        'request_number': req.request_number,
        'service': req.service.name,
        'status': req.status,
        'status_display': status_display,
        'requested_at': req.requested_at.strftime('%Y-%m-%d %H:%M'),
    }
    return JsonResponse(data)

from django.views.decorators.http import require_POST

@csrf_exempt
@require_POST
def create_update_mission(request, request_id):
    service_request = get_object_or_404(ServiceRequest, pk=request_id)
    try:
        mission = RequsetMission.objects.get(service_request=service_request)
        form = MissionForm(request.POST, instance=mission)
    except RequsetMission.DoesNotExist:
        form = MissionForm(request.POST)

    if form.is_valid():
        mission = form.save(commit=False)
        mission.service_request = service_request
        mission.customer = service_request.card.customer
        mission.service = service_request.service
        mission.contact_phone = service_request.contact_phone
        
        mission.save()

        # Update the service request status to 'inprogress'
        if service_request.status != 'inprogress':
            service_request.status = 'inprogress'
            service_request.save()

        return JsonResponse({'success': True, 'mission_id': mission.id})
    else:
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

class AddBonusQuotaView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = ServiceQuota
    form_class = BonusQuotaForm
    template_name = 'cards/includes/add_bonus_modal.html'  # used for AJAX only

    def test_func(self):
        return self.request.user.is_staff

    def dispatch(self, request, *args, **kwargs):
        self.card = get_object_or_404(Card, pk=self.kwargs.get('card_pk'))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['card'] = self.card
        return kwargs

    def form_valid(self, form):
        # Check if quota already exists for this card+service
        quota, created = ServiceQuota.objects.get_or_create(
            card=self.card,
            service=form.cleaned_data['service'],
            defaults={
                'remaining_uses': form.cleaned_data['remaining_uses'],
                'total_provided': form.cleaned_data['remaining_uses'],
              
            }
        )
        if not created:
            # Add to existing quota
            quota.remaining_uses += form.cleaned_data['remaining_uses']
            quota.total_provided += form.cleaned_data['remaining_uses']
           
            quota.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect('card_detail', pk=self.card.pk)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors})
        return super().form_invalid(form)
    
class ServiceRequestListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = ServiceRequest
    template_name = 'cards/request_list.html'
    context_object_name = 'requests'
    paginate_by = 20
    ordering = ['-requested_at']

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        queryset = super().get_queryset().select_related('card', 'service', 'card__customer')
        q = self.request.GET.get('q', '')
        if q:
            queryset = queryset.filter(
                Q(request_number__icontains=q) |
                Q(card__number_card__icontains=q) |
                Q(card__customer__name__icontains=q) |
                Q(service__name__icontains=q)
            )
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = ServiceRequest.STATUS_CHOICES
        context['query_params'] = self.request.GET.copy()
        if 'page' in context['query_params']:
            del context['query_params']['page']
        context['active_tab'] ='cards'
        context['drivers'] = Drivers.objects.all().order_by('name')
        
        return context

class UpdateRequestStatusView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = ServiceRequest
    form_class = RequestStatusUpdateForm
    template_name = 'cards/includes/update_request_status_modal.html'

    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect('request_list')

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors})
        return super().form_invalid(form)
    

from django.http import JsonResponse
from .models import Service

def get_services_by_category(request):
    category_id = request.GET.get('category_id')
    if category_id:
        try:
            default_quota = CategoryCard.objects.values_list('default_quota', flat=True).get(pk=category_id)
        except CategoryCard.DoesNotExist:
            default_quota = 1
        services = [
            {'id': s['id'], 'name': s['name'], 'default_quota': default_quota}
            for s in Service.objects.filter(category_id=category_id).values('id', 'name')
        ]
        return JsonResponse({'services': services})
    return JsonResponse({'services': []})



from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import Card, Service, ServiceQuota

@csrf_exempt
@require_POST
def add_service_quota(request, card_id):
    card = get_object_or_404(Card, pk=card_id)
    service_id = request.POST.get('service')
    quantity = request.POST.get('quantity')

    if not service_id or not quantity:
        return JsonResponse({'success': False, 'error': 'Service and quantity are required.'}, status=400)

    try:
        service = Service.objects.get(pk=service_id)
    except Service.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Service not found.'}, status=404)

    try:
        quantity = int(quantity)
        if quantity < 1:
            raise ValueError
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Quantity must be a positive integer.'}, status=400)

    # Get or create the quota
    quota, created = ServiceQuota.objects.get_or_create(
        card=card,
        service=service,
        defaults={'remaining_uses': quantity, 'total_provided': quantity}
    )
    if not created:
        # Add to existing quota
        quota.remaining_uses += quantity
        quota.total_provided += quantity
        quota.save()

    return JsonResponse({'success': True, 'quota_id': quota.id})


class CardReportView(LoginRequiredMixin, TemplateView):
    template_name = 'cards/reports/card_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        start_date = self.request.GET.get('start')
        end_date = self.request.GET.get('end')
        category_id = self.request.GET.get('category')
        search = self.request.GET.get('q', '').strip()

        cards = Card.objects.select_related('customer', 'category').all()

        if start_date:
            cards = cards.filter(created_at__date__gte=start_date)
        if end_date:
            cards = cards.filter(created_at__date__lte=end_date)
        if category_id:
            cards = cards.filter(category_id=category_id)
        if search:
            cards = cards.filter(
                Q(customer__name__icontains=search) |
                Q(vehicle_number__icontains=search) |
                Q(chassis_number__icontains=search) |
                Q(type_car__icontains=search) |
                Q(color_car__icontains=search)
            )

        context['cards'] = cards
        context['categories'] = CategoryCard.objects.all()
        context['total_value'] = sum(card.category.price if card.category else 0 for card in cards)
        context['active_tab'] = 'cards'
        return context


# ---------- Services Provided Report ----------
class ServiceReportView(LoginRequiredMixin, TemplateView):
    template_name = 'cards/reports/service_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        start_date = self.request.GET.get('start')
        end_date = self.request.GET.get('end')
        service_id = self.request.GET.get('service')

        requests = ServiceRequest.objects.select_related('card', 'service', 'card__customer').all()

        if start_date:
            requests = requests.filter(requested_at__date__gte=start_date)
        if end_date:
            requests = requests.filter(requested_at__date__lte=end_date)
        if service_id:
            requests = requests.filter(service_id=service_id)

        context['requests'] = requests
        context['services'] = Service.objects.all()
        context['active_tab'] ='cards'
        return context


# ---------- Card Lookup ----------
class CardLookupView(LoginRequiredMixin, TemplateView):
    template_name = 'cards/reports/card_lookup.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        search_by = self.request.GET.get('by', 'number')

        if query:
            if search_by == 'number':
                cards = Card.objects.filter(number_card__icontains=query)
            elif search_by == 'chassis':
                cards = Card.objects.filter(chassis_number__icontains=query)
            elif search_by == 'vehicle':
                cards = Card.objects.filter(vehicle_number__icontains=query)
            elif search_by == 'customer':
                cards = Card.objects.filter(customer__name__icontains=query)
            else:
                cards = Card.objects.none()

            context['cards'] = cards.select_related('customer', 'category')
            context['active_tab'] ='cards'
        return context
    
from django.contrib.auth.decorators import login_required
@login_required
def check_new_requests(request):
    # إذا كان المستخدم ليس staff، لا نرسل شيئاً
    if not request.user.is_staff:
        return JsonResponse({'count': 0})

    # الحصول على آخر وقت شوهد أو إنشاء سجل جديد
    last_seen, created = UserLastSeen.objects.get_or_create(user=request.user)
    
    # حساب عدد الطلبات الجديدة بعد آخر وقت شوهد
    new_count = ServiceRequest.objects.filter(requested_at__gt=last_seen.last_request_time).count()
    
    # تحديث وقت آخر شوهد إلى الآن (لكن نؤجل التحديث حتى نرسل العداد)
    # سنقوم بالتحديث فقط عندما يقوم المستخدم بفتح القائمة أو النقر على الجرس
    
    return JsonResponse({'count': new_count})

@login_required
def mark_requests_seen(request):
    # تحديث آخر وقت شوهد إلى الآن (عند النقر على الجرس)
    if request.user.is_staff:
        last_seen, _ = UserLastSeen.objects.get_or_create(user=request.user)
        last_seen.last_request_time = timezone.now()
        last_seen.save()
    return JsonResponse({'status': 'ok'})