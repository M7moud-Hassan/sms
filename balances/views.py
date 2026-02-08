from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Max
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, FileResponse
from django.urls import reverse
from django.contrib import messages
import os
import openpyxl
from django.conf import settings
from django.db.models import Sum, Max, Q, F, Value as V, CharField, DecimalField, OuterRef, Subquery
import subprocess
import pandas as pd
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from recipt_vouchers.models import Vouchers, Attachments
from drivers.models import Drivers, PMission, SMission
from customers.models import Customers
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
        pmission = PMission.objects.filter(Q(date=date) & Q(car_num=car_num) & Q(car_type=car_type) & Q(from_location=from_location) & Q(to_location=to_location))
        if not pmission:
            new_pmission = PMission(customer=customer, employee=employee, date=date, from_location=from_location, to_location=to_location, car_type=car_type, car_mark=car_mark, car_num=car_num, car_color=car_color, notes=notes)
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