from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
import os, io
from .reports_pdf import build_customers_pdf, build_drivers_pdf
from django.conf import settings
from collections import defaultdict
from django.contrib.auth import authenticate, login, logout
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Max
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, FileResponse, Http404
from django.urls import reverse
from django.contrib import messages
import os
import openpyxl
from django.conf import settings
from django.db.models import Sum, Max, Q, F, Value as V, CharField, DecimalField, OuterRef, Subquery, Count
import pandas as pd
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from recipt_vouchers.models import Vouchers, Attachments
from drivers.models import Drivers, PMission, SMission
from customers.models import Customers, CostCenter
from invoices.models import Invoices
from suppliers.models import Invoices as Inv

def index(request):
    # Get today's date
    today = datetime.today()
    last_six_months = [(today - timedelta(days=i * 30)).strftime('%Y-%m') for i in range(6)][::-1]
    # Subtract 12 months from today's date
    date_12_months_ago = today - relativedelta(months=12)
    date_1_month_ago = today - relativedelta(months=1)
    # Format the date as 'YYYY-MM-DD'
    last_year = date_12_months_ago.strftime('%Y-%m-%d')
    last_month = date_1_month_ago.strftime('%Y-%m-%d')
    today = today.strftime('%Y-%m-%d')
    income_data = []
    costs_data = []
    for month in last_six_months:
        # Filter transactions for income and costs for the month
        income = Invoices.objects.filter(date__startswith=month).aggregate(Sum('tamount'))['tamount__sum'] or 0
        cost = Inv.objects.filter(date__startswith=month).aggregate(Sum('tamount'))['tamount__sum'] or 0
        # Append the results to the corresponding lists
        income_data.append(float(income))
        costs_data.append(float(cost))
    year_earning = Invoices.objects.filter(date__range=(last_year, today)).aggregate(Sum('tamount'))['tamount__sum'] or 0
    month_earning = Invoices.objects.filter(date__range=(last_month, today)).aggregate(Sum('tamount'))['tamount__sum'] or 0
    vouchers = Vouchers.objects.filter(Q(invoice__exported__isnull=False) & Q(invoice__date__range=(last_year, today)))
    car_vouchers = vouchers.filter(car_type__icontains="ar").count()
    cycle_vouchers = vouchers.filter(car_type__icontains="cyc").count()
    drivers_balance = Drivers.objects.aggregate(Sum('balance'))['balance__sum'] or 0
    customers_balance = Customers.objects.aggregate(Sum('balance'))['balance__sum'] or 0
    #active_tab = 'pmissions' if 'jobbox' in username else request.GET.get('active_tab', 'balances')
    context = {
        'active_tab': 'balances',  # Set this to the name of the active tab
        'months': last_six_months,
        'income_data': income_data,
        'costs_data': costs_data,
        'year_earning': year_earning,
        'month_earning': month_earning,
        'car_vouchers': car_vouchers,
        'cycle_vouchers': cycle_vouchers,
        'drivers_balance': drivers_balance,
        'customers_balance': customers_balance,
    }
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('balances_index')
        else:
            customer = Customers.objects.filter(Q(username=username) & Q(password=password)).first()
            if customer:
                related_url = reverse('job_index', kwargs={'username': username, 'password': password})
                return HttpResponseRedirect(related_url)
            else:
                messages.success(request, "There was an error for username or password...")
                return redirect('balances_index')
    else:
        username = request.user.username
        if 'jobbox' in username:
            return redirect('pmissions_index')
        else:
            return render(request, "balances/dashboard.html", context)

def job_index(request, username, password):
    customer = Customers.objects.filter(Q(username=username) & Q(password=password)).first()
    pre_pmissions1 = PMission.objects.filter(customer__id=customer.id).distinct('car_mark')
    pre_pmissions2 = PMission.objects.filter(customer__id=customer.id).distinct('car_color')
    pre_pmissions3 = PMission.objects.filter(customer__id=customer.id).distinct('from_location')
    pre_pmissions4 = PMission.objects.filter(customer__id=customer.id).distinct('to_location')
    employee = ""
    from_location = ""
    to_location = ""
    last_pmission = PMission.objects.filter(customer__id=customer.id).last()
    if last_pmission:
        employee = last_pmission.employee
        from_location = last_pmission.from_location
        to_location = last_pmission.to_location
    pmissions = PMission.objects.filter(Q(customer__id=customer.id) & (Q(mmission__isnull=True) | (Q(mmission__smission__car_num=F('car_num')) & Q(mmission__smission__receipt__isnull=False)))).exclude(mmission__smission__receipt="Invoiced")
    pmissions = pmissions.annotate(smission_receipt=Subquery(SMission.objects.filter(mmission=OuterRef('mmission')).values('receipt')[:1]))
    cost_centers = CostCenter.objects.filter(customer__id=customer.id).order_by('name')
    customer_context = {
        'customer': customer,
        'pre_pmissions1': pre_pmissions1,
        'pre_pmissions2': pre_pmissions2,
        'pre_pmissions3': pre_pmissions3,
        'pre_pmissions4': pre_pmissions4,
        'pmissions': pmissions,
        'employee': employee,
        'from_location': from_location,
        'to_location': to_location,
        'cost_centers': cost_centers,
    }
    return render(request, "drivers/job_box.html", customer_context)

def add_pmission(request, customer_id):
    customer = Customers.objects.filter(id=customer_id).first()
    username = customer.username
    password = customer.password
    if request.method == 'POST':
        employee = request.POST.get('employee')
        from_location = request.POST.get('from_location')
        to_location = request.POST.get('to_location')
        date = request.POST.get('date')
        car_type = request.POST.get('car_type')
        car_mark = request.POST.get('car_mark')
        car_num = request.POST.get('car_num')
        car_color = request.POST.get('car_color')
        notes = request.POST.get('notes')
        cost_center = CostCenter.objects.filter(id=request.POST.get('cost_center') or None, customer=customer).first()
        pmission = PMission.objects.filter(Q(date=date) & Q(car_num=car_num) & Q(car_type=car_type) & Q(from_location=from_location) & Q(to_location=to_location))
        if not pmission:
            new_pmission = PMission(customer=customer, employee=employee, date=date, from_location=from_location, to_location=to_location, car_type=car_type, car_mark=car_mark, car_num=car_num, car_color=car_color, notes=notes, cost_center=cost_center)
            new_pmission.save()
    related_url = reverse('job_index', kwargs={'username': username, 'password': password})
    return HttpResponseRedirect(related_url)

def import_excel(request, id):
    errors = []
    customer = Customers.objects.filter(id=id).first()
    username = customer.username
    password = customer.password
    related_url = reverse('job_index', kwargs={'username': username, 'password': password})
    if request.method == "POST" and 'excelFile' in request.FILES:
        excel_file = request.FILES['excelFile']
        try:
            df = pd.read_excel(excel_file)
            df = df.fillna("")
            # Check for duplicates in the DataFrame
            duplicates = df[df.duplicated(subset=[df.columns[1], df.columns[2], df.columns[3], df.columns[6]], keep=False)]
            if not duplicates.empty:
                errors.append("بيانات مكررة...")
            # Check for existing records in the database
            for index, row in df.iterrows():
                car_num = row[df.columns[6]]
                from_location = row[df.columns[2]]
                to_location = row[df.columns[3]]
                date = row[df.columns[1]]
                # Handle invalid or non-date values
                if pd.isnull(date) or not isinstance(date, pd.Timestamp):
                    errors.append("توجد أخطاء في صيغة التاريخ بأحد صفوف الملف...")
                else:
                    # Format the date as 'YYYY-MM-DD'
                    date = date.strftime('%Y-%m-%d')
                    # Check for duplicate entries in the database
                    if PMission.objects.filter(Q(car_num=car_num) & Q(date=date) & Q(from_location=from_location) & Q(to_location=to_location)).exists():
                        errors.append("بيانات مكررة...")
            if errors:
                # Pass the errors as JSON
                return render(request, 'drivers/job_box.html', {
                    'customer': customer,
                    'related_url': related_url,
                    'errors_json': json.dumps(errors)  # Convert errors to JSON
                })
            # Save valid data
            for index, row in df.iterrows():
                PMission.objects.create(
                    customer=customer,
                    employee=row[df.columns[0]],
                    date=row[df.columns[1]],
                    from_location=row[df.columns[2]],
                    to_location=row[df.columns[3]],
                    car_type=row[df.columns[4]],
                    car_mark=row[df.columns[5]],
                    car_num=row[df.columns[6]],
                    car_color=row[df.columns[7]],
                    notes=row[df.columns[8]]
                )
        except Exception as e:
            errors.append("خطأ ببيانات الملف...")
            return render(request, 'drivers/job_box.html', {
                'customer': customer,
                'related_url': related_url,
                'errors_json': json.dumps(errors)
            })

    return HttpResponseRedirect(related_url)

def edit_pmission(request, id, customer_id):
    customer = Customers.objects.filter(id=customer_id).first()
    username = customer.username
    password = customer.password
    if request.method == 'POST':
        pmission = PMission.objects.filter(id=id).first()
        pmission.employee = request.POST.get('employee')
        pmission.from_location = request.POST.get('from_location')
        pmission.to_location = request.POST.get('to_location')
        pmission.date = request.POST.get('date')
        pmission.car_type = request.POST.get('car_type')
        pmission.car_mark = request.POST.get('car_mark')
        pmission.car_num = request.POST.get('car_num')
        pmission.car_color = request.POST.get('car_color')
        pmission.notes = request.POST.get('notes')
        pmission.cost_center = CostCenter.objects.filter(id=request.POST.get('cost_center') or None, customer=customer).first()
        pmission.created_at = datetime.now()
        tpmission = PMission.objects.exclude(id=id)
        if not tpmission:
            pmission.save()
        else:
            queryset = tpmission.filter(Q(date=request.POST.get('date')) & Q(car_num=request.POST.get('car_num')) & Q(car_type=request.POST.get('car_type')) & Q(from_location=request.POST.get('from_location')) & Q(to_location=request.POST.get('to_location')))
            if queryset.exists():
                record = queryset.first()  # This will get the first object that matches the query
            else:
                record = None
            if not record:
                pmission.save()
    related_url = reverse('job_index', kwargs={'username': username, 'password': password})
    return HttpResponseRedirect(related_url)

def add_cost_center(request, customer_id):
    customer = Customers.objects.filter(id=customer_id).first()
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        if not name:
            return JsonResponse({'success': False, 'error': 'الاسم مطلوب'}, status=400)
        if CostCenter.objects.filter(customer=customer, name=name).exists():
            return JsonResponse({'success': False, 'error': 'مركز التكلفة موجود مسبقاً'}, status=400)
        cc = CostCenter.objects.create(customer=customer, name=name)
        return JsonResponse({'success': True, 'id': cc.id, 'name': cc.name})
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

def delete_cost_center(request, id, customer_id):
    customer = Customers.objects.filter(id=customer_id).first()
    if request.method == 'POST':
        CostCenter.objects.filter(id=id, customer=customer).delete()
        return JsonResponse({'success': True, 'id': id})
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

def delete_pmission(request, id, customer_id):
    customer = Customers.objects.filter(id=customer_id).first()
    username = customer.username
    password = customer.password
    try:
        if request.method == 'POST':
            pmission = PMission.objects.filter(id=id).first()
            pmission.delete()
    except:
        pass
    related_url = reverse('job_index', kwargs={'username': username, 'password': password})
    return HttpResponseRedirect(related_url)

def logout_user(request):
    logout(request)
    return redirect('balances_index')

@login_required
def top_customers_pdf(request, date_from, date_to):
    # vehicles handled per customer (voucher count, via the voucher's invoice)
    vehicle_rows = (
        Vouchers.objects
        .filter(invoice__date__range=(date_from, date_to), invoice__require_id__isnull=False)
        .values('invoice__require_id', 'invoice__require_id__name')
        .annotate(vehicles=Count('id'))
    )
    # revenue per customer (summed on Invoices directly, so tamount isn't inflated by the voucher join)
    revenue_rows = (
        Invoices.objects
        .filter(date__range=(date_from, date_to), require_id__isnull=False)
        .values('require_id', 'require_id__name')
        .annotate(revenue=Sum('tamount'))
    )
    merged = defaultdict(lambda: {'name': '', 'vehicles': 0, 'revenue': 0})
    for r in vehicle_rows:
        cid = r['invoice__require_id']
        merged[cid]['name'] = r['invoice__require_id__name']
        merged[cid]['vehicles'] = r['vehicles']
    for r in revenue_rows:
        cid = r['require_id']
        merged[cid]['name'] = r['require_id__name']
        merged[cid]['revenue'] = r['revenue'] or 0
    rows = sorted(merged.values(), key=lambda x: x['revenue'], reverse=True)

    buf = io.BytesIO()
    build_customers_pdf(
        buf, rows, date_from, date_to,
        total_vehicles=sum(x['vehicles'] for x in rows),
        total_revenue=sum(x['revenue'] for x in rows),
    )
    buf.seek(0)
    response = HttpResponse(buf.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Top Customers {date_from} to {date_to}.pdf"'
    return response

@login_required
def top_drivers_pdf(request, date_from, date_to):
    rows = (
        Vouchers.objects
        .filter(invoice__date__range=(date_from, date_to), invoice__driver__isnull=False)
        .values('invoice__driver', 'invoice__driver__name')
        .annotate(vehicles=Count('id'))
        .order_by('-vehicles')
    )
    rows = [{'name': r['invoice__driver__name'], 'vehicles': r['vehicles']} for r in rows]

    buf = io.BytesIO()
    build_drivers_pdf(
        buf, rows, date_from, date_to,
        total_vehicles=sum(x['vehicles'] for x in rows),
    )
    buf.seek(0)
    response = HttpResponse(buf.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Top Drivers {date_from} to {date_to}.pdf"'
    return response

def _ranking_data(date_from, date_to):
    # vehicles handled per customer (voucher count via the voucher's invoice)
    cust_vehicles = {
        r['invoice__require_id']: r['vehicles']
        for r in Vouchers.objects
            .filter(invoice__date__range=(date_from, date_to), invoice__require_id__isnull=False)
            .values('invoice__require_id').annotate(vehicles=Count('id'))
    }
    # revenue per customer (summed on Invoices, so tamount isn't inflated by the voucher join)
    cust_rev = (Invoices.objects
        .filter(date__range=(date_from, date_to), require_id__isnull=False)
        .values('require_id', 'require_id__name')
        .annotate(revenue=Sum('tamount'))
        .order_by('-revenue')[:10])
    # vehicles transported per driver
    drv = (Vouchers.objects
        .filter(invoice__date__range=(date_from, date_to), invoice__driver__isnull=False)
        .values('invoice__driver__name')
        .annotate(vehicles=Count('id'))
        .order_by('-vehicles')[:10])
    return {
        'customers_labels': [r['require_id__name'] for r in cust_rev],
        'customers_revenue': [float(r['revenue'] or 0) for r in cust_rev],
        'customers_vehicles': [cust_vehicles.get(r['require_id'], 0) for r in cust_rev],
        'drivers_labels': [r['invoice__driver__name'] for r in drv],
        'drivers_vehicles': [r['vehicles'] for r in drv],
    }

@login_required
def ranking_data(request):
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if not date_from or not date_to:
        return JsonResponse({'error': 'date_from and date_to required'}, status=400)
    return JsonResponse(_ranking_data(date_from, date_to))