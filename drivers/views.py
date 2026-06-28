from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Max, Q, F, Value as V, CharField, DecimalField, Count
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, FileResponse, Http404
from django.urls import reverse
import os
import pytz
from django.utils.timezone import localtime
import openpyxl
from django.conf import settings
import subprocess
import zipfile
import json
from django.views.decorators.http import require_POST
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from datetime import datetime, timedelta
from collections import OrderedDict
from .forms import SearchForm
from .models import Drivers, Treasury, MMission, SMission, PMission, UNAVAILABLE_STATUSES
from customers.models import Customers
from recipt_vouchers.models import Vouchers
from invoices.models import Invoices, Items
from invoices.helpers import n2w, update_invoice

# Create your views here.
def index(request):
    new_treasury = Treasury.objects.aggregate(Max('number'))['number__max']
    if new_treasury is None:
        # If no records exist in the table, set the invoice number to 1
        new_treasury = 1
    else:
        # Add 1 to the maximum invoice number
        new_treasury += 1
    drivers = Drivers.objects.all().order_by('-balance')
    form = SearchForm(request.GET)
    result = None
    if "search" in request.GET:
        result = "ok"
        if form.is_valid():
            query = form.cleaned_data['query']
            try:
                query_value = float(query)
                drivers = drivers.filter(Q(number__icontains=query) | Q(balance__gte=query_value))
            except:
                drivers = drivers.filter(Q(name__icontains=query) | Q(username__icontains=query))
    number_of_drivers = drivers.count()
    total_balances = drivers.aggregate(Sum('balance'))['balance__sum'] or 0
    context = {
        'form': form,
        'new_treasury': new_treasury,
        'drivers': drivers,
        'result': result,
        'number_of_drivers': number_of_drivers,
        'total_balances': total_balances,
        'active_tab': 'drivers'  # Set this to the name of the active tab
    }
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('drivers_index')
        else:
            messages.success(request, "There was an error for username or password...")
            return redirect('drivers_index')
    username = request.user.username
    if 'jobbox' in username:
        return redirect('pmissions_index')
    else:
        return render(request, "drivers/index.html", context)

def get_invoices(request):
    driver_id = request.GET.get('driver_id')
    invoices = Invoices.objects.filter(Q(type="نقدي") & Q(driver__id=driver_id) & Q(tamount__gt=F('driver_paid')))
    invoice_list = list(invoices.values('number'))
    return JsonResponse({'invoices': invoice_list})

def get_invoice_details(request):
    invoice_number = request.GET.get('invoice_number')
    invoice = Invoices.objects.filter(number=invoice_number).first()
    if invoice:
        amount_due = invoice.tamount - invoice.driver_paid
        return JsonResponse({'amount_due': amount_due})
    return JsonResponse({'amount_due': 0})

def driver_balance(request, id):
    driver_name = get_object_or_404(Drivers, id=id).name
    invoices = Invoices.objects.filter(Q(driver__name=driver_name) & Q(type="نقدي"))
    treasury = Treasury.objects.filter(driver__name=driver_name)
    total_invoiced = invoices.aggregate(Sum('tamount'))['tamount__sum'] or 0
    total_treasury = treasury.aggregate(Sum('amount'))['amount__sum'] or 0
    required_amount = total_invoiced - total_treasury
    context = {
        'id': id,
        'driver_name': driver_name,
        'required_amount': required_amount,
        'invoices': invoices,
        'treasury': treasury,
        'active_tab': 'drivers',
        'total_invoiced': total_invoiced,
        'total_treasury': total_treasury
    }
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('drivers_index')
        else:
            messages.success(request, "There was an error for username or password...")
            return redirect('drivers_index')
    else:
        return render(request, "drivers/balance.html", context)

@login_required
def add_driver(request):
    if request.method == 'POST':
        name = request.POST.get('name').strip()
        username = request.POST.get('username')
        password = request.POST.get('password')
        queryset = Drivers.objects.filter(Q(username=username) & Q(password=password))
        if queryset.exists():
            record = queryset.first()  # This will get the first object that matches the query
        else:
            record = None
        # Add the new item to the database
        if record:
            messages.success(request, "Repeated Username and Password...")
        else:
            new_driver = Drivers(
                name=name, username=username, password=password,
                status=request.POST.get('status') or "Available",
                status_from=request.POST.get('status_from') or None,
                status_to=request.POST.get('status_to') or None,
            )
            new_driver.save()
            update_driver_balance(name)
    return redirect('drivers_index')

@login_required
def edit_driver(request, id):
    if request.method == 'POST':
        item = get_object_or_404(Drivers, id=id)
        if item.name != request.POST.get('name').strip():
            vouchers = Vouchers.objects.filter(driver_name=item.name)
            if vouchers:
                for voucher in vouchers:
                    voucher.driver_name = request.POST.get('name').strip()
                    voucher.save()
            item.name = request.POST.get('name').strip()
        item.status = request.POST.get('status')
        item.status_from = request.POST.get('status_from') or None
        item.status_to = request.POST.get('status_to') or None
        item.username = request.POST.get('username')
        item.password = request.POST.get('password')
        tdriver = Drivers.objects.exclude(id=id)
        if not tdriver:
            item.save()
        else:
            queryset = tdriver.filter(Q(username=request.POST.get('username')) & Q(password=request.POST.get('password')))
            if queryset.exists():
                record = queryset.first()  # This will get the first object that matches the query
            else:
                record = None
            if record:
                messages.success(request, "Repeated Username and Password...")
            else:
                item.save()
    return redirect('drivers_index')

@login_required
def delete_driver(request, id):
    item = get_object_or_404(Drivers, id=id)
    if request.method == 'POST':
        item.delete()
    return redirect('drivers_index')

@login_required
def add_treasury(request):
    if request.method == 'POST':
        driver_id = request.POST.get('driver_id')
        driver = get_object_or_404(Drivers, id=driver_id)
        invoice_number = request.POST.get('invoice_number')
        invoice = get_object_or_404(Invoices, number=invoice_number)
        number = request.POST.get('number')
        amount = request.POST.get('amount')
        payment = request.POST.get('method')
        # Add the new item to the database
        new_treasury = Treasury(driver=driver, invoice=invoice, number=number, amount=amount, payment=payment)
        new_treasury.save()
        update_driver_balance(driver.name)
        update_invoice(invoice.id)
    return redirect('drivers_index')

@login_required
def edit_treasury(request, id):
    if request.method == 'POST':
        item = get_object_or_404(Treasury, id=id)
        item.amount = request.POST.get('edit-amount')
        item.payment = request.POST.get('method')
        item.save()
        driver_name = request.POST.get('driver')
        update_driver_balance(driver_name)
        update_invoice(item.invoice.id)
        related_url = reverse('driver_balance', kwargs={'id': request.POST.get('driver_id')})
        return HttpResponseRedirect(related_url)

@login_required
def delete_treasury(request, id):
    item = get_object_or_404(Treasury, id=id)
    invoice_id = item.invoice.id
    if request.method == 'POST':
        item.delete()
        driver_name = request.POST.get('driver')
        update_driver_balance(driver_name)
        update_invoice(invoice_id)
        related_url = reverse('driver_balance', kwargs={'id': request.POST.get('driver_id')})
        return HttpResponseRedirect(related_url)

@login_required
def export_treasury(request, id, date_from, date_to):
    driver = get_object_or_404(Drivers, id=id)
    driver_name = driver.name
    amman_tz = pytz.timezone('Asia/Amman')

    start_dt = datetime.strptime(date_from, '%Y-%m-%d')
    end_dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)

    # Mirror filter_invoices EXACTLY (the page's source of truth):
    #   invoices : driver's نقدي invoices dated in the window
    #   treasury : payments toward THOSE invoices (linked via invoice__driver),
    #              only نقدي, dated by the invoice's date — NOT Treasury.driver/created_at
    invoices = Invoices.objects.filter(
        Q(driver__id=id) & Q(type="نقدي") & Q(created_at__date__range=(date_from, date_to))
    ).annotate(
        account=V('فاتورة', output_field=CharField()),
        number_annotated=F('number'),
        amount_annotated=F('tamount'),
        created_at_annotated=F('created_at'),
    ).values('account', 'number_annotated', 'amount_annotated', 'created_at_annotated')

    treasury = Treasury.objects.filter(
        Q(invoice__driver__id=id) & Q(invoice__type="نقدي") & Q(invoice__created_at__date__range=(date_from, date_to))
    ).annotate(
        account=V('سداد', output_field=CharField()),
        number_annotated=F('invoice__number'),
        amount_annotated=F('amount'),
        created_at_annotated=F('created_at'),
    ).values('account', 'number_annotated', 'amount_annotated', 'created_at_annotated')

    entries = []
    for e in invoices.union(treasury).order_by('created_at_annotated'):
        entries.append({
            'account': e['account'],
            'number': e['number_annotated'],
            'amount': e['amount_annotated'],
            'created_at': localtime(e['created_at_annotated'], amman_tz),
        })
    total_invoiced = invoices.aggregate(Sum('amount_annotated'))['amount_annotated__sum'] or 0
    total_treasury = treasury.aggregate(Sum('amount_annotated'))['amount_annotated__sum'] or 0
    required_amount = total_invoiced - total_treasury

    # ---- transported vehicles & trips come from Vouchers (delivered transports) ----
    # driver match: Vouchers.driver_name == driver.name ; period: receipt_to_time in window
    from recipt_vouchers.models import Vouchers   # adjust to the real app label if different
    from collections import OrderedDict

    voucher_qs = list(
        Vouchers.objects.filter(
            driver_name=driver_name,
            receipt_to_time__range=(start_dt, end_dt),
        ).select_related('car_owner', 'invoice').order_by('receipt_to_time')
    )

    # VEHICLES report: one row per voucher = one transported vehicle
    vehicles = [{
        'date': v.receipt_to_time,
        'customer': v.car_owner.name if v.car_owner else '',
        'car_type': v.car_type, 'car_mark': v.car_mark,
        'car_num': v.car_num, 'car_color': v.car_color,
    } for v in voucher_qs]
    vehicles_count = len(vehicles)

    # TRIPS report: one trip per invoice; invoice-less vouchers each count as their own trip.
    # Built from the SAME voucher_qs, so the two reports are always consistent:
    #   sum(trip.vehicles) == vehicles_count
    groups = OrderedDict()
    for v in voucher_qs:
        key = ('inv', v.invoice_id) if v.invoice_id is not None else ('novoice', v.id)
        g = groups.get(key)
        if g is None:
            g = {
                'date': v.receipt_to_time,
                'customer': v.car_owner.name if v.car_owner else '',
                'from_location': _short_loc(v.receipt_from_location),
                'to_location': _short_loc(v.receipt_to_location),
                'vehicles': 0,
                'cost': 0.0,
            }
            groups[key] = g
        g['vehicles'] += 1
        # invoice total counted once per trip (first voucher of the group)
        if v.invoice_id is not None and g['vehicles'] == 1 and v.invoice and v.invoice.tamount:
            g['cost'] += float(v.invoice.tamount)

    trips = list(groups.values())
    trips_count = len(trips)
    total_trip_cost = sum(t['cost'] for t in trips)

    # ---- summary income = invoiced total (consistent with the balance page) ----
    total_income = total_invoiced

    # ---- build the four ReportLab PDFs into one zip ----
    import io
    from . import driver_reports as dr

    # Read selected reports from query string, e.g. ?reports=account_statement,trips
    selected = request.GET.get('reports', '')
    selected_keys = [s.strip() for s in selected.split(',') if s.strip()]

    available = {
        "account_statement": (
            "account_statement.pdf",
            lambda b: dr.build_account_statement_pdf(b, driver_name, date_from, date_to,
                                                      entries, total_invoiced, total_treasury, required_amount)),
        "trips": (
            "trips.pdf",
            lambda b: dr.build_trips_pdf(b, driver_name, date_from, date_to, trips, total_trip_cost)),
        "vehicles": (
            "vehicles.pdf",
            lambda b: dr.build_vehicles_pdf(b, driver_name, date_from, date_to, vehicles)),
        "summary": (
            "summary.pdf",
            lambda b: dr.build_summary_pdf(b, driver_name, date_from, date_to,
                                           total_income, vehicles_count, trips_count)),
    }

    # default: all reports (backwards compatibility)
    if not selected_keys:
        selected_keys = list(available.keys())

    chosen = [available[k] for k in selected_keys if k in available]
    if not chosen:
        raise Http404("No valid report selected")

    if len(chosen) == 1:
        # single file -> direct PDF download
        name, build = chosen[0]
        buf = io.BytesIO()
        build(buf)
        buf.seek(0)
        response = HttpResponse(buf.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{name}"'
        response.set_cookie('export_download_done', 'true', max_age=60)
        return response

    # multiple files -> zip
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, build in chosen:
            b = io.BytesIO()
            build(b)
            zf.writestr(name, b.getvalue())

    zip_buf.seek(0)
    response = HttpResponse(zip_buf.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="Driver_Report_{driver_name}.zip"'
    response.set_cookie('export_download_done', 'true', max_age=60)
    return response

def _short_loc(text, max_len=40):
    """Pick a concise label from a long comma-separated address:
    prefer the last 1-2 segments (area/city), capped at max_len."""
    if not text:
        return ''
    parts = [p.strip() for p in str(text).split(',') if p.strip()]
    if not parts:
        return str(text)[:max_len]
    label = parts[-1]
    # add the previous segment if there's room and it adds detail
    if len(parts) >= 2 and len(parts[-2]) + len(label) + 2 <= max_len:
        label = parts[-2] + ', ' + label
    return label[:max_len]

@login_required
def missions_index(request, id):
    drivers = Drivers.objects.all()
    driver = drivers.filter(id=id).first()
    driver_name = driver.name
    missions = MMission.objects.filter(Q(driver__id=id) & Q(receipt__isnull=True))
    missions_count = missions.count()
    customers = Customers.objects.all()
    adjusted_missions = []
    for mission in missions:
        mission.adjusted_count = SMission.objects.filter(Q(mmission__id=mission.id) & Q(receipt="Assigned")).count()
        adjusted_missions.append(mission)
    context = {
        'id': id,
        'drivers': drivers,
        'driver_name': driver_name,
        'missions': adjusted_missions,
        'missions_count': missions_count,
        'customers': customers,
        'active_tab': 'drivers'
    }
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('missions_index')
        else:
            messages.success(request, "There was an error for username or password...")
            return redirect('missions_index')
    else:
        return render(request, "drivers/missions_index.html", context)

@login_required
def mission_details(request, id):
    mission = get_object_or_404(MMission, id=id)
    items = SMission.objects.filter(Q(mmission__id=id) & Q(receipt="Assigned"))
    driver = mission.driver
    customer = mission.customer
    transportation_date = mission.date
    receiving_location = mission.from_location
    delivery_location = mission.to_location
    estimated_cost = mission.cost
    count_of_vehicles = items.count()
    context = {
               'id': id,
               'items':items,
               'driver':driver,
               'customer':customer,
               'transportation_date':transportation_date,
               'receiving_location':receiving_location,
               'delivery_location':delivery_location,
               'estimated_cost':estimated_cost,
               'count_of_vehicles':count_of_vehicles,
               'active_tab': 'drivers'
               }
    return render(request, "drivers/details.html", context)

@login_required
def add_new_mission(request):
    if request.method == 'POST':
        driver_name = request.POST.get('driver')
        mission_date = request.POST.get('date')
        driver_obj = Drivers.objects.filter(name=driver_name).first()
        if driver_obj and mission_date and not driver_obj.is_available(
            datetime.strptime(mission_date, '%Y-%m-%d').date()
        ):
            messages.success(request, "Driver is unavailable on the selected date...")
            return redirect('pmissions_index')
        missions_count = MMission.objects.filter(Q(driver__name=driver_name) & Q(date__lte=datetime.today())).count() + 1
        description = driver_name + " " + str(missions_count)
        driver = get_object_or_404(Drivers, name=driver_name)
        customer_name = request.POST.get('name')
        customer = get_object_or_404(Customers, name=customer_name)
        date = request.POST.get('date')
        from_location = request.POST.get('receiving_location')
        to_location = request.POST.get('delivery_location')
        cost = request.POST.get('cost')
        notes = request.POST.get('notes')
        created_by = request.user.username
        new_mission = MMission(description=description, driver=driver, customer=customer, date=date, from_location=from_location, to_location=to_location, cost=cost, scost=get_string(float(cost)), notes=notes, created_by=created_by)
        new_mission.save()
    return redirect('pmissions_index')

@login_required
def add_mission(request, id):
    if request.method == 'POST':
        driver = get_object_or_404(Drivers, id=id)
        customer_name = request.POST.get('name')
        customer_phone = request.POST.get('phone')
        date = request.POST.get('date')
        from_location = request.POST.get('receiving_location')
        to_location = request.POST.get('delivery_location')
        cost = request.POST.get('cost')
        notes = request.POST.get('notes')
        created_by = request.user.username
        queryset = Customers.objects.filter(Q(name=customer_name)|Q(phone=customer_phone))
        if queryset.exists():
            customer = queryset.first()
        else:
            customer = Customers(name=customer_name, phone=customer_phone, created_by=request.user.username)
            customer.save()
        new_mission = MMission(driver=driver, customer=customer, date=date, from_location=from_location, to_location=to_location, cost=cost, scost=get_string(float(cost)), notes=notes, created_by=created_by)
        new_mission.save()
        related_url = reverse('mission_details', kwargs={'id': new_mission.id})
        return HttpResponseRedirect(related_url)

@login_required
def edit_mission(request, id):
    if request.method == 'POST':
        mission = get_object_or_404(MMission, id=id)
        driver = Drivers.objects.filter(name=request.POST.get('driver')).first()
        driver_id = driver.id
        customer_name = request.POST.get('name')
        customer_phone = request.POST.get('phone')
        mission.description = request.POST.get('description')
        mission.driver = driver
        mission.date = request.POST.get('date')
        mission.from_location = request.POST.get('receiving_location')
        mission.to_location = request.POST.get('delivery_location')
        mission.cost = request.POST.get('cost')
        mission.scost = get_string(float(request.POST.get('cost')))
        mission.notes = request.POST.get('notes')
        mission.created_by = request.user.username
        queryset = Customers.objects.filter(Q(name=customer_name) | Q(phone=customer_phone))
        if queryset.exists():
            customer = queryset.first()
        else:
            customer = Customers(name=customer_name, phone=customer_phone)
            customer.save()
        mission.customer = customer
        mission.save()
        related_url = reverse('missions_index', kwargs={'id': driver_id})
        return HttpResponseRedirect(related_url)

@login_required
def delete_mission(request, id):
    if request.method == 'POST':
        mission = get_object_or_404(MMission, id=id)
        driver_id = mission.driver.id
        mission.delete()
        related_url = reverse('missions_index', kwargs={'id': driver_id})
        return HttpResponseRedirect(related_url)

@login_required
def add_mitem(request, id):
    if request.method == 'POST':
        mission = get_object_or_404(MMission, id=id)
        type = request.POST.get('type')
        mark = request.POST.get('mark')
        number = request.POST.get('number').strip()
        color = request.POST.get('color')
        user = request.user.username
        new_item = SMission(mmission=mission, car_type=type, car_mark=mark, car_num=number, car_color=color , created_by=user)
        new_item.save()
        missions_count = SMission.objects.filter(Q(mmission__id=id) & Q(receipt="Assigned")).count()
        mission.count = missions_count
        mission.save()
        related_url = reverse('mission_details', kwargs={'id': mission.id})
        return HttpResponseRedirect(related_url)

@login_required
def edit_mitem(request, id):
    if request.method == 'POST':
        item = get_object_or_404(SMission, id=id)
        item.car_type = request.POST.get('type')
        item.car_mark = request.POST.get('mark')
        item.car_num = request.POST.get('number').strip()
        item.car_color = request.POST.get('color')
        item.created_by = request.user.username
        item.save()
        mission_id = item.mmission.id
        related_url = reverse('mission_details', kwargs={'id': mission_id})
        return HttpResponseRedirect(related_url)

@login_required
def delete_mitem(request, id):
    if request.method == 'POST':
        item = get_object_or_404(SMission, id=id)
        mission = item.mmission
        item.delete()
        missions_count = SMission.objects.filter(Q(mmission__id=item.mmission.id) & Q(receipt="Assigned")).count()
        mission.count = missions_count
        mission.save()
        related_url = reverse('mission_details', kwargs={'id': mission.id})
        return HttpResponseRedirect(related_url)

@login_required
def pmissions_index(request):
    pmissions = PMission.objects.filter(
        Q(date__gte=datetime.today()) & (
            Q(mmission__isnull=True) |
            (Q(mmission__isnull=False) & Q(mmission__count__gt=0) & Q(mmission__accept__isnull=True))
        )
    ).order_by('customer__name', 'date', 'id')

    mmissions = MMission.objects.filter(date__gte=datetime.today())
    amman_tz = pytz.timezone('Asia/Amman')
    adjusted_pmissions = []
    for pmission in pmissions:
        pmission.created_at = localtime(pmission.created_at, amman_tz)
        pmission.adjusted_created_at = pmission.created_at
        time_diff = pmission.created_at.utcoffset().total_seconds() / 3600
        if pmission.created_at:
            pmission.adjusted_created_at += timedelta(hours=time_diff)
        # Fetch MMissions matching this PMission, excluding any whose driver is
        # unavailable ON THIS PMission's date (not "today").
        matching_mmissions = MMission.objects.filter(
            Q(date=pmission.date) & Q(customer__id=pmission.customer.id) & Q(accept__isnull=True)
        ).exclude(
            Q(driver__status__in=UNAVAILABLE_STATUSES)
            & (Q(driver__status_from__isnull=True) | Q(driver__status_from__lte=pmission.date))
            & (Q(driver__status_to__isnull=True) | Q(driver__status_to__gte=pmission.date))
        )
        # Attach the options to the PMission object
        pmission.mmission_options = matching_mmissions
        adjusted_pmissions.append(pmission)
    drivers = Drivers.objects.all()
    # Customers that can log into the Job Box (have username + password)
    job_customers = Customers.objects.filter(
        username__isnull=False, password__isnull=False
    ).exclude(username='').exclude(password='').order_by('name')
    # Fetch distinct customer IDs from PMission and then get the full Customer objects
    unique_customer_ids = pmissions.values_list('customer', flat=True).distinct()
    customers = Customers.objects.filter(id__in=unique_customer_ids)
    # Fetch distinct from_location and to_location for suggestions
    location_data = {
        customer.id: {
            'from_locations': PMission.objects.filter(customer=customer).values_list('from_location', flat=True).distinct(),
            'to_locations': PMission.objects.filter(customer=customer).values_list('to_location', flat=True).distinct()
        }
        for customer in customers
    }
    context = {
        'mmissions': mmissions,
        'pmissions': adjusted_pmissions,
        'drivers': drivers,
        'customers': customers,
        'job_customers': job_customers,
        'location_data': location_data,
        'active_tab': 'pmissions'  # Set this to the name of the active tab
    }
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('pmissions_index')
        else:
            messages.success(request, "There was an error for username or password...")
            return redirect('pmissions_index')
    return render(request, "drivers/pmissions.html", context)

@login_required
def update_pmission_mmission(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    from django.db import transaction

    pmission_id = request.POST.get('pmission_id')
    mmission_id = request.POST.get('mmission_id')
    other_notes = request.POST.get('other_notes')

    try:
        with transaction.atomic():
            pmission = PMission.objects.select_for_update().get(id=pmission_id)
            car_num = (pmission.car_num or '').strip()
            user = request.user.username

            # 1) Detach from the OLD mission: remove THIS pmission's SMission,
            #    scoped to the mission it is CURRENTLY linked to (not any same-day
            #    match) so another driver's row is never touched.
            old_mmission = pmission.mmission
            if old_mmission:
                SMission.objects.filter(
                    mmission=old_mmission,
                    car_type=pmission.car_type,
                    car_num=car_num,
                ).delete()
                old_mmission.count = SMission.objects.filter(
                    mmission=old_mmission, receipt="Assigned"
                ).count()
                old_mmission.save()

            # 2) Attach to the NEW mission (if chosen), creating its SMission.
            if mmission_id:
                mmission = MMission.objects.select_for_update().get(id=mmission_id)
                already = SMission.objects.filter(
                    mmission=mmission, car_type=pmission.car_type, car_num=car_num
                ).exists()
                if not already:
                    SMission.objects.create(
                        mmission=mmission,
                        car_type=pmission.car_type,
                        car_mark=pmission.car_mark,
                        car_num=car_num,
                        car_color=pmission.car_color,
                        created_by=user,
                    )
                pmission.mmission = mmission
                mmission.count = SMission.objects.filter(
                    mmission=mmission, receipt="Assigned"
                ).count()
                mmission.save()
            else:
                mmission = None
                pmission.mmission = None

            # 3) Notes + save the pmission ONCE, consistently.
            pmission.another_notes = other_notes if other_notes else None
            pmission.save()

        return JsonResponse({
            'status': 'success',
            'mmission_description': (
                other_notes if other_notes
                else (mmission.description if mmission_id else '')
            ),
        })
    except PMission.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'PMission not found'}, status=404)
    except MMission.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'MMission not found'}, status=404)

@login_required
def fetch1(request):
    try:
        name = request.GET.get('name')
        customer = Customers.objects.filter(name=name).first()
        phone = customer.phone
        address = customer.address
    except:
        phone = None
        address = None
    return JsonResponse({'phone': phone, 'address': address})

def get_location_suggestions(request):
    customer_name = request.GET.get('customer_name')
    date = request.GET.get('date')
    if not customer_name or not date:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    # Fetch the customer by name
    try:
        customer = Customers.objects.get(name=customer_name)  # Assumes name is unique
    except Customers.DoesNotExist:
        return JsonResponse({'error': 'Customer not found'}, status=404)
    # Fetch distinct from_location and to_location based on customer and date
    from_locations = PMission.objects.filter(customer=customer, date=date).values_list('from_location', flat=True).distinct()
    to_locations = PMission.objects.filter(customer=customer, date=date).values_list('to_location', flat=True).distinct()
    return JsonResponse({
        'from_locations': list(from_locations),
        'to_locations': list(to_locations),
    })

def filter_invoices(request, id):
    date_from = datetime.strptime(request.GET.get('date_from'), '%Y-%m-%d')
    date_to = datetime.strptime(request.GET.get('date_to'), '%Y-%m-%d')
    invoices = Invoices.objects.filter(Q(driver__id=id) & Q(type="نقدي") & Q(date__range=(date_from, date_to))).select_related('require_id').order_by('number')
    amman_tz = pytz.timezone('Asia/Amman')
    invoices_data = []
    for invoice in invoices:
        invoice.created_at = localtime(invoice.created_at, amman_tz)
        invoices_data.append({
            'number': invoice.number,
            'require_id__name': invoice.require_id.name,
            'tamount': invoice.tamount,
            'created_at': invoice.created_at
        })
    treasury = Treasury.objects.filter(Q(invoice__driver__id=id) & Q(invoice__type="نقدي") & Q(invoice__date__range=(date_from, date_to))).select_related('invoice').order_by('created_at')
    treasury_data = []
    for tr in treasury:
        tr.created_at = localtime(tr.created_at, amman_tz)
        treasury_data.append({
            'id': tr.id,
            'number': tr.number,
            'inumber': tr.invoice.number,
            'amount': tr.amount,
            'payment': tr.payment,
            'created_at': tr.created_at
        })
    total_invoiced = invoices.aggregate(Sum('tamount'))['tamount__sum'] or 0
    total_treasury = treasury.aggregate(Sum('amount'))['amount__sum'] or 0
    required_amount = total_invoiced - total_treasury
    return JsonResponse({'invoices': invoices_data, 'treasury': treasury_data, 'total_invoiced': total_invoiced, 'total_treasury': total_treasury, 'required_amount': required_amount}, safe=False)

def fetch_pmissions(request):
    #pmissions = PMission.objects.all()  # Fetch unread missions
    pmissions = PMission.objects.filter(read=False)  # Fetch unread missions
    pmissions_data = []
    for mission in pmissions:
        pmissions_data.append({
            'id': mission.id,
            'customer_name': mission.customer.name,
            'date': mission.date.strftime('%Y-%m-%d') if mission.date else '',
            'from_location': mission.from_location,
            'to_location': mission.to_location,
            'car_type': mission.car_type,
            'car_num': mission.car_num
        })
    return JsonResponse({'pmissions': pmissions_data})

def mark_as_read(request, mission_id):
    if request.method == 'POST':
        try:
            mission = PMission.objects.get(id=mission_id)
            mission.read = True
            mission.save()
            return JsonResponse({'status': 'success', 'message': 'Mission marked as read.'})
        except PMission.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Mission not found.'})

@require_POST
def mark_as_read_bulk(request):
    try:
        data = json.loads(request.body or '{}')
        ids = data.get('ids', [])
        ids = [int(i) for i in ids]
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid ids'}, status=400)

    if not ids:
        return JsonResponse({'updated': 0})

    updated = PMission.objects.filter(id__in=ids).update(read=True)
    return JsonResponse({'updated': updated})

def update_driver_balance(driver_name):
    driver = get_object_or_404(Drivers, name=driver_name)
    total_invoiced = Invoices.objects.filter(Q(driver__name=driver_name) & Q(type="نقدي")).aggregate(Sum('tamount'))['tamount__sum'] or 0
    total_treasury = Treasury.objects.filter(driver__name=driver_name).aggregate(Sum('amount'))['amount__sum'] or 0
    driver.balance = total_invoiced - total_treasury
    driver.save()

def get_string(amount):
    sdinar = int(amount)
    sfils = (amount - int(amount)) * 100
    samount = "فقط وقدره صفر دينار لا غير"
    if sfils > 0:
        samount = "فقط وقدره " + n2w(sdinar) + ' دينار و ' + n2w(sfils) + ' فلس لا غير'
    elif sdinar > 0:
        samount = "فقط وقدره " + n2w(sdinar) + ' دينار لا غير'
    return samount

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def my_view(request):
    # Your view logic
    user = request.user  # Assuming you want to send a message to this user
    message = "A new notification!"

    # Send a message to the WebSocket group for this user
    channel_layer = get_channel_layer()
    group_name = f'user_{user.id}'

    # Use async_to_sync to call async channel layer method from sync view
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'send_notification',  # This corresponds to the method in your consumer
            'message': message,
        }
    )

    return JsonResponse({'status': 'success', 'message': 'Notification sent!'})

@login_required
def change_pmission_customer(request, id):
    if request.method == 'POST':
        pmission = get_object_or_404(PMission, id=id)
        new_customer = Customers.objects.filter(id=request.POST.get('customer')).first()
        if new_customer:
            pmission.customer = new_customer
            pmission.save()
            return JsonResponse({'success': True, 'customer_id': new_customer.id})
    return JsonResponse({'success': False}, status=400)