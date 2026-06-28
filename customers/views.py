from django.shortcuts import render, redirect, get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Max, Q, F, Value as V, CharField, DecimalField, OuterRef, Subquery
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, FileResponse, Http404
import io
from django.urls import reverse
from django.contrib.auth.decorators import login_required
import os
import openpyxl
from django.conf import settings
import subprocess
import zipfile
from django.core.files.storage import FileSystemStorage
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
import pytz
import pandas as pd
from django.utils.timezone import localtime, now
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from .forms import SearchForm, ExcelUploadForm
from drivers.models import PMission, SMission
from recipt_vouchers.models import Vouchers
from .models import Customers, Papers, Treasury
from invoices.models import Invoices, Items
from invoices.helpers import update_invoice

# ===== amount -> Arabic words (Jordanian Dinar / Fils) =====
_ONES = ["", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة",
         "عشرة", "أحد عشر", "اثنا عشر", "ثلاثة عشر", "أربعة عشر", "خمسة عشر",
         "ستة عشر", "سبعة عشر", "ثمانية عشر", "تسعة عشر"]
_TENS = ["", "", "عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون"]
_HUNDREDS = ["", "مئة", "مئتان", "ثلاثمئة", "أربعمئة", "خمسمئة", "ستمئة", "سبعمئة", "ثمانمئة", "تسعمئة"]


def _three(n):
    parts = []
    h, rem = divmod(n, 100)
    if h:
        parts.append(_HUNDREDS[h])
    if rem:
        if rem < 20:
            parts.append(_ONES[rem])
        else:
            t, o = divmod(rem, 10)
            parts.append((_ONES[o] + " و" + _TENS[t]) if o else _TENS[t])
    return " و".join(parts)


def _scale(count, singular, dual, plural_3_10, plural_11_up):
    """Apply Arabic number-noun agreement for a scale word (thousand/million/...).
    1 -> singular, 2 -> dual, 3..10 -> 'X plural', 11+ -> 'X singular'."""
    if count == 1:
        return singular
    if count == 2:
        return dual
    if 3 <= count <= 10:
        return _three(count) + " " + plural_3_10
    return _three(count) + " " + plural_11_up


def _arabic_int(n):
    if n == 0:
        return "صفر"
    out = []
    billions, n = divmod(n, 1_000_000_000)
    millions, n = divmod(n, 1_000_000)
    thousands, hundreds = divmod(n, 1000)
    if billions:
        out.append(_scale(billions, "مليار", "ملياران", "مليارات", "مليار"))
    if millions:
        out.append(_scale(millions, "مليون", "مليونان", "ملايين", "مليون"))
    if thousands:
        out.append(_scale(thousands, "ألف", "ألفان", "آلاف", "ألف"))
    if hundreds:
        out.append(_three(hundreds))
    return " و".join(out)

def amount_to_arabic_words(dinars, fils):
    text = "فقط وقدره " + _arabic_int(int(dinars)) + " دينار"
    if int(fils):
        text += " و" + _arabic_int(int(fils)) + " فلس"
    return text + " لا غير"

def index(request):
    new_treasury = Treasury.objects.aggregate(Max('number'))['number__max']
    if new_treasury is None:
        # If no records exist in the table, set the invoice number to 1
        new_treasury = 1
    else:
        # Add 1 to the maximum invoice number
        new_treasury += 1
    customers = Customers.objects.filter(balance__gt=0).order_by('-balance')
    form = SearchForm(request.GET)
    result = None
    options = "option0"
    if "search" in request.GET:
        result = "ok"
        if form.is_valid():
            if request.GET['inlineRadioOptions'] == "option1":
                customers = Customers.objects.filter(payment="ذمم").order_by('-balance')
                options = "option1"
            elif request.GET['inlineRadioOptions'] == "option2":
                customers = Customers.objects.filter(payment="نقدي").order_by('-balance')
                options = "option2"
            query = form.cleaned_data['query']
            customers = customers.filter(
                Q(name__icontains=query) | Q(phone__icontains=query) |
                Q(mail__icontains=query) | Q(notes__icontains=query) |
                Q(username__icontains=query) |
                Q(vouchers__car_num__icontains=query)
            ).distinct()
    number_of_customers = customers.count()
    total_balances = customers.aggregate(Sum('balance'))['balance__sum'] or 0
    context = {
        'active_tab': 'customers',
        'new_treasury': new_treasury,
        'result': result,
        'options': options,
        'form': form,
        'customers': customers,
        'number_of_customers': number_of_customers,
        'total_balances': total_balances
    }
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('customers_index')
        else:
            messages.success(request, "There was an error for username or password...")
            return redirect('customers_index')
    else:
        username = request.user.username
        if 'jobbox' in username:
            return redirect('pmissions_index')
        else:
            return render(request, "customers/index.html", context)

def get_invoices(request):
    customer_id = request.GET.get('customer_id')
    invoices = Invoices.objects.filter(Q(type="ذمم") & Q(require_id__id=customer_id) & Q(tamount__gt=F('customer_paid')))
    invoice_list = list(invoices.values('number'))
    return JsonResponse({'invoices': invoice_list})

def get_invoice_details(request):
    invoice_number = request.GET.get('invoice_number')
    invoice = Invoices.objects.filter(number=invoice_number).first()
    if invoice:
        amount_due = invoice.tamount - invoice.customer_paid
        return JsonResponse({'amount_due': amount_due})
    return JsonResponse({'amount_due': 0})

def customer_details(request, id):
    customer = get_object_or_404(Customers, id=id)
    papers = Papers.objects.filter(customer__id=id)
    vouchers = Vouchers.objects.filter(car_owner__id=id).distinct('car_num', 'car_type')
    invoices = Invoices.objects.filter(Q(require_id__id=id) & Q(type="ذمم")).annotate(
        account=V('Created invoice', output_field=CharField()),
        number_annotated=F('number'),
        amount_annotated=F('tamount'),
        created_at_annotated=F('created_at')
    ).values(
        'account',
        'number_annotated',
        'amount_annotated',
        'created_at_annotated'
    )
    treasury = Treasury.objects.filter(customer__id=id).annotate(
        account=V('Paid to treasury', output_field=CharField()),
        number_annotated=F('number'),
        amount_annotated=F('amount'),
        created_at_annotated=F('created_at')
    ).values(
        'account',
        'number_annotated',
        'amount_annotated',
        'created_at_annotated'
    )
    combined_entries = invoices.union(treasury).order_by('created_at_annotated')
    context = {
        'active_tab': 'customers',
        'id': id,
        'vouchers': vouchers,
        'customer': customer,
        'papers': papers,
        'combined_entries': combined_entries,
    }
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('customers_index')
        else:
            messages.success(request, "There was an error for username or password...")
            return redirect('customers_index')
    else:
        return render(request, "customers/details.html", context)

def customer_balance(request, id):
    customer = get_object_or_404(Customers, id=id)
    customer_name = customer.name
    invoices = Invoices.objects.filter(Q(require_id__id=id) & Q(type="ذمم"))
    treasury = Treasury.objects.filter(customer__id=id)
    total_invoiced = invoices.aggregate(Sum('tamount'))['tamount__sum'] or 0
    total_treasury = treasury.aggregate(Sum('amount'))['amount__sum'] or 0
    required_amount = total_invoiced - total_treasury
    context = {
        'id': id,
        'customer_name': customer_name,
        'required_amount': required_amount,
        'invoices': invoices,
        'treasury': treasury,
        'active_tab': 'customers',
        'total_invoiced': total_invoiced,
        'total_treasury': total_treasury,
        'cost_centers': customer.cost_centers.all().order_by('name'),
    }
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('customers_index')
        else:
            messages.success(request, "There was an error for username or password...")
            return redirect('customers_index')
    else:
        return render(request, "customers/balance.html", context)

@login_required
def add_customer(request):
    if request.method == 'POST':
        name = request.POST.get('customer_name').strip()
        address = request.POST.get('customer_address')
        mail = request.POST.get('customer_mail')
        phone = request.POST.get('customer_phone')
        payment = request.POST.get('customer_payment')
        username = request.POST.get('username')
        password = request.POST.get('password')
        notes = request.POST.get('customer_notes')
        logo = request.FILES.get('customer_logo')
        system_user = request.user.username
        if username and password and mail:
            queryset = Customers.objects.filter(Q(name=name) | Q(phone=phone) | Q(mail=mail) | (Q(username=username) & Q(password=password)))
        elif username and password:
            queryset = Customers.objects.filter(Q(name=name) | Q(phone=phone) | (Q(username=username) & Q(password=password)))
        elif mail:
            queryset = Customers.objects.filter(Q(name=name) | Q(phone=phone) | Q(mail=mail))
        else:
            queryset = Customers.objects.filter(Q(name=name) | Q(phone=phone))
        if queryset.exists():
            record = queryset.first()  # This will get the first object that matches the query
        else:
            record = None
        if record:
            messages.success(request, "Repeated Data...")
        else:
            if logo:
                fs = FileSystemStorage()
                logo_name = fs.save(logo.name, logo)
                # Save to the database
                Customers.objects.create(name=name, mail=mail, phone=phone, address=address, username=username, password=password, notes=notes, payment=payment, logo=logo_name, created_by=system_user)
            else:
                Customers.objects.create(name=name, mail=mail, phone=phone, address=address, username=username, password=password, notes=notes, payment=payment, created_by=system_user)
    return redirect('customers_index')

@login_required
def edit_customer(request, id):
    customer = get_object_or_404(Customers, id=id)
    if request.method == 'POST':
        customer.name = request.POST.get('name').strip()
        customer.address = request.POST.get('address')
        customer.phone = request.POST.get('phone')
        customer.mail = request.POST.get('mail')
        customer.payment = request.POST.get('payment')
        customer.username = request.POST.get('username')
        customer.password = request.POST.get('password')
        customer.notes = request.POST.get('notes')
        customer_logo = request.FILES.get('logo')
        if customer_logo:
            fs = FileSystemStorage()
            logo_name = fs.save(customer_logo.name, customer_logo)
            customer.logo = logo_name
        tcustomer = Customers.objects.exclude(id=id)
        if not tcustomer:
            customer.save()
        else:
            if request.POST.get('username') and request.POST.get('password') and request.POST.get('mail'):
                queryset = tcustomer.filter(Q(name=request.POST.get('name')) | Q(phone=request.POST.get('phone')) | Q(mail=request.POST.get('mail')) | (Q(username=request.POST.get('username')) & Q(password=request.POST.get('password'))))
            elif request.POST.get('username') and request.POST.get('password'):
                queryset = tcustomer.filter(Q(name=request.POST.get('name')) | Q(phone=request.POST.get('phone')) | (Q(username=request.POST.get('username')) & Q(password=request.POST.get('password'))))
            elif request.POST.get('mail'):
                queryset = tcustomer.filter(Q(name=request.POST.get('name')) | Q(phone=request.POST.get('phone')) | Q(mail=request.POST.get('mail')))
            else:
                queryset = tcustomer.filter(Q(name=request.POST.get('name')) | Q(phone=request.POST.get('phone')))
            if queryset.exists():
                record = queryset.first()  # This will get the first object that matches the query
            else:
                record = None
            if record:
                messages.success(request, "Repeated Data...")
            else:
                customer.save()
    return redirect('customers_index')

@login_required
def add_attachment(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        customer = get_object_or_404(Customers, id=customer_id)
        description = request.POST.get('description')
        attachment = request.FILES.get('attachment')
        fs = FileSystemStorage()
        attachment_name = fs.save(attachment.name, attachment)
        # Save to the database
        Papers.objects.create(customer=customer, description=description, paper=attachment_name)
        related_url = reverse('customer_details', kwargs={'id': customer_id})
        return HttpResponseRedirect(related_url)

@login_required
def edit_attachment(request, id):
    paper = get_object_or_404(Papers, id=id)
    if request.method == 'POST':
        customer_id = paper.customer.id
        paper.description = request.POST.get('description')
        customer_paper = request.FILES.get('paper')
        if customer_paper:
            fs = FileSystemStorage()
            paper_name = fs.save(customer_paper.name, customer_paper)
            paper.paper = paper_name
        paper.save()
        related_url = reverse('customer_details', kwargs={'id': customer_id})
        return HttpResponseRedirect(related_url)

@login_required
def delete_attachment(request, id):
    paper = get_object_or_404(Papers, id=id)
    if request.method == 'POST':
        customer_id = paper.customer.id
        paper.delete()
        related_url = reverse('customer_details', kwargs={'id': customer_id})
        return HttpResponseRedirect(related_url)

@login_required
def add_treasury(request):
    if request.method == 'POST':
        customer_id = request.POST['customer_id']
        customer = get_object_or_404(Customers, id=customer_id)
        invoice_number = request.POST['invoice_number']
        invoice = get_object_or_404(Invoices, number=invoice_number)
        number = request.POST['number']
        amount = request.POST['amount']
        payment = request.POST['method']
        # Add the new item to the database
        new_treasury = Treasury(customer=customer, invoice=invoice, number=number, amount=amount, payment=payment)
        new_treasury.save()
        update_customer_balance(customer_id)
        update_invoice(invoice.id)
    return redirect('customers_index')

@login_required
def edit_treasury(request, id):
    if request.method == 'POST':
        customer_id = request.POST['customer_id']
        item = get_object_or_404(Treasury, id=id)
        item.amount = request.POST['edit-amount']
        item.payment = request.POST['method']
        item.save()
        update_customer_balance(customer_id)
        update_invoice(item.invoice.id)
        related_url = reverse('customer_balance', kwargs={'id': customer_id})
        return HttpResponseRedirect(related_url)

@login_required
def delete_treasury(request, id):
    item = get_object_or_404(Treasury, id=id)
    invoice_id = item.invoice.id
    if request.method == 'POST':
        customer_id = request.POST['customer_id']
        item.delete()
        update_customer_balance(customer_id)
        update_invoice(invoice_id)
        related_url = reverse('customer_balance', kwargs={'id': customer_id})
        return HttpResponseRedirect(related_url)

@login_required
def export_treasury(request, id, date_from, date_to):
    customer = get_object_or_404(Customers, id=id)
    customer_name = customer.name
    amman_tz = pytz.timezone('Asia/Amman')

    def _lt(dt):
        return localtime(dt, amman_tz) if dt else None

    # ---- 0) account statement (invoices + treasury) ----
    inv_q = Invoices.objects.filter(
        Q(require_id__id=id) & Q(type="ذمم") & Q(date__range=(date_from, date_to))
    ).annotate(
        account=V('فاتورة', output_field=CharField()),
        number_annotated=F('number'),
        amount_annotated=F('tamount'),
        created_at_annotated=F('created_at'),
    ).values('account', 'number_annotated', 'amount_annotated', 'created_at_annotated')

    tre_q = Treasury.objects.filter(
        Q(customer__id=id) & Q(invoice__date__range=(date_from, date_to))
    ).annotate(
        account=V('سداد', output_field=CharField()),
        number_annotated=F('invoice__number'),
        amount_annotated=F('amount'),
        created_at_annotated=F('created_at'),
    ).values('account', 'number_annotated', 'amount_annotated', 'created_at_annotated')

    entries = [{
        'account': e['account'], 'number': e['number_annotated'],
        'amount': e['amount_annotated'], 'created_at': _lt(e['created_at_annotated']),
    } for e in inv_q.union(tre_q).order_by('created_at_annotated')]
    total_invoiced = inv_q.aggregate(Sum('amount_annotated'))['amount_annotated__sum'] or 0
    total_treasury = tre_q.aggregate(Sum('amount_annotated'))['amount_annotated__sum'] or 0
    required_amount = total_invoiced - total_treasury

    # ---- 1) vehicles transported (delivered vouchers) ----
    veh_q = Vouchers.objects.filter(
        car_owner__id=id, receipt_to_time__date__range=(date_from, date_to)
    ).order_by('receipt_to_time')
    vehicles = [{
        'date': _lt(v.receipt_to_time), 'car_type': v.car_type, 'car_mark': v.car_mark,
        'car_num': v.car_num, 'car_color': v.car_color,
    } for v in veh_q]

    # ---- 2) transport transactions (full lifecycle) ----
    txn_q = Vouchers.objects.filter(car_owner__id=id).filter(
        Q(receipt_from_time__date__range=(date_from, date_to)) |
        Q(receipt_to_time__date__range=(date_from, date_to))
    ).order_by('receipt_from_time')
    txns = [{
        'number': v.number, 'car_mark': v.car_mark, 'car_num': v.car_num,
        'from_name': v.recipient_from_name, 'from_location': v.receipt_from_location,
        'from_time': _lt(v.receipt_from_time),
        'to_name': v.recipient_to_name, 'to_location': v.receipt_to_location,
        'to_time': _lt(v.receipt_to_time), 'driver_name': v.driver_name,
    } for v in txn_q]

    # ---- 3) task timeline (PMission entry + voucher start/completion) ----
    # PMission and Vouchers share no FK; matched here on car_num.
    v_by_num = {v.car_num: v for v in Vouchers.objects.filter(car_owner__id=id)}
    pms = PMission.objects.filter(
        customer__id=id, created_at__date__range=(date_from, date_to)
    ).select_related('customer').order_by('created_at')
    tasks = []
    for p in pms:
        v = v_by_num.get(p.car_num)
        tasks.append({
            'entered_at': _lt(p.created_at),
            'start_date': _lt(v.receipt_from_time) if (v and v.receipt_from_time) else None,
            'completion_date': _lt(v.receipt_to_time) if (v and v.receipt_to_time) else None,
            'requester': p.employee,
            'chassis': p.car_num,
        })

    # ---- 4/5/6) invoices / outstanding / paid ----
    inv_rows = list(Invoices.objects.filter(
        require_id__id=id, type="ذمم", date__range=(date_from, date_to)
    ).order_by('-date').values('number', 'date', 'driver__name', 'tamount', 'customer_paid'))

    def _paid(r):
        return float(r['tamount'] or 0) > 0 and float(r['customer_paid'] or 0) >= float(r['tamount'] or 0)

    invoices_all = inv_rows
    paid_rows = [r for r in inv_rows if _paid(r)]
    # outstanding = ALL unpaid for the customer (NOT limited to the period)
    outstanding_rows = list(Invoices.objects.filter(
        require_id__id=id, type="ذمم", tamount__gt=F('customer_paid')
    ).order_by('-date').values('number', 'date', 'driver__name', 'tamount', 'customer_paid'))

    # ---- build the selected reports ----
    from . import customer_reports as cr
    available = {
        "account_statement": ("account_statement.pdf",
            lambda b: cr.build_account_statement_pdf(b, customer_name, date_from, date_to,
                                                     entries, total_invoiced, total_treasury, required_amount)),
        "vehicles": ("vehicles.pdf",
            lambda b: cr.build_vehicles_pdf(b, customer_name, date_from, date_to, vehicles)),
        "transactions": ("transactions.pdf",
            lambda b: cr.build_transactions_pdf(b, customer_name, date_from, date_to, txns)),
        "timeline": ("timeline.pdf",
            lambda b: cr.build_timeline_pdf(b, customer_name, date_from, date_to, tasks)),
        "invoices": ("invoices.pdf",
            lambda b: cr.build_invoices_pdf(b, customer_name, date_from, date_to, invoices_all)),
        "outstanding": ("outstanding.pdf",
            lambda b: cr.build_outstanding_pdf(b, customer_name, date_from, date_to, outstanding_rows)),
        "paid": ("paid.pdf",
            lambda b: cr.build_paid_pdf(b, customer_name, date_from, date_to, paid_rows)),
    }

    selected = [s.strip() for s in request.GET.get('reports', '').split(',') if s.strip()]
    if not selected:
        selected = list(available.keys())
    chosen = [available[k] for k in selected if k in available]
    if not chosen:
        raise Http404("No valid report selected")

    if len(chosen) == 1:
        name, build = chosen[0]
        buf = io.BytesIO(); build(buf); buf.seek(0)
        response = HttpResponse(buf.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{name}"'
        response.set_cookie('export_download_done', 'true', max_age=60)
        return response

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, build in chosen:
            b = io.BytesIO(); build(b); zf.writestr(name, b.getvalue())
    zip_buf.seek(0)
    response = HttpResponse(zip_buf.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="Customer_Report_{customer_name}.zip"'
    response.set_cookie('export_download_done', 'true', max_age=60)
    return response

def filter_invoices(request, id):
    date_from = datetime.strptime(request.GET.get('date_from'), '%Y-%m-%d')
    date_to = datetime.strptime(request.GET.get('date_to'), '%Y-%m-%d')
    cost_center = (request.GET.get('cost_center') or '').strip()
    amman_tz = pytz.timezone('Asia/Amman')

    invoices = Invoices.objects.filter(
        require_id__id=id, type="ذمم", date__range=(date_from, date_to)
    )
    treasury = Treasury.objects.filter(
        invoice__require_id__id=id, invoice__type="ذمم",
        invoice__date__range=(date_from, date_to),
    )

    # optional cost-center filter (cost center lives on PMission, reached via the
    # invoice's vouchers: voucher.car_num <-> pmission.car_num) — one JOIN, no N+1
    if cost_center:
        cc_car_nums = list(
            PMission.objects.filter(cost_center_id=cost_center)
            .exclude(car_num__isnull=True).exclude(car_num__exact='')
            .values_list('car_num', flat=True)
        )
        invoices = invoices.filter(vouchers__car_num__in=cc_car_nums).distinct()
        treasury = treasury.filter(invoice__vouchers__car_num__in=cc_car_nums).distinct()

    # Period totals — these drive the TABLES only, not the headline balance.
    total_invoiced = invoices.aggregate(Sum('tamount'))['tamount__sum'] or 0
    total_treasury = treasury.aggregate(Sum('amount'))['amount__sum'] or 0
    required_amount = total_invoiced - total_treasury

    # .values() fetches driver__name / invoice__number via a JOIN:
    # one query per table instead of one query per row.
    invoices_data = [
        {
            'number': row['number'],
            'driver__name': row['driver__name'],
            'tamount': row['tamount'],
            'created_at': localtime(row['created_at'], amman_tz),
        }
        for row in invoices.order_by('number').values(
            'number', 'driver__name', 'tamount', 'created_at'
        )
    ]
    treasury_data = [
        {
            'id': row['id'],
            'number': row['number'],
            'inumber': row['invoice__number'],
            'amount': row['amount'],
            'payment': row['payment'],
            'created_at': localtime(row['created_at'], amman_tz),
        }
        for row in treasury.order_by('created_at').values(
            'id', 'number', 'invoice__number', 'amount', 'payment', 'created_at'
        )
    ]

    return JsonResponse({
        'invoices': invoices_data,
        'treasury': treasury_data,
        'total_invoiced': total_invoiced,
        'total_treasury': total_treasury,
        'required_amount': required_amount,
    }, safe=False)

def export_combined_invoice(request, id):
    customer = get_object_or_404(Customers, id=id)

    raw = request.POST.get('invoices', '') or request.GET.get('invoices', '')
    numbers = [n.strip() for n in raw.split(',') if n.strip()]
    if not numbers:
        return JsonResponse({'error': 'No invoices selected.'}, status=400)

    invoices = list(
        Invoices.objects.filter(require_id__id=id, type="ذمم", number__in=numbers).order_by('number')
    )
    if not invoices:
        return JsonResponse({'error': 'No matching invoices found.'}, status=400)

    invoice_ids = [inv.id for inv in invoices]

    # ---- resolve cost centers for ALL selected invoices in a few bulk queries ----
    # 1) vouchers tied to these invoices  (invoice_id -> car_num)
    voucher_rows = list(
        Vouchers.objects.filter(invoice_id__in=invoice_ids)
        .exclude(car_num__isnull=True).exclude(car_num__exact='')
        .values('invoice_id', 'car_num')
    )
    car_nums = {vr['car_num'].strip() for vr in voucher_rows}

    # 2) PMission cost-center name per (mmission_id, car_num) + per-car fallback (one query)
    pm_by_mission_car = {}     # (mmission_id, car_num) -> cost center name
    pm_by_car = {}             # car_num -> latest cost center name (fallback)
    if car_nums:
        for pm in (PMission.objects
                   .filter(car_num__in=car_nums, cost_center__isnull=False)
                   .values('mmission_id', 'car_num', 'cost_center__name')
                   .order_by('id')):
            cn = (pm['car_num'] or '').strip()
            name_ = pm['cost_center__name']
            if pm['mmission_id'] is not None:
                pm_by_mission_car[(pm['mmission_id'], cn)] = name_
            pm_by_car[cn] = name_       # later rows overwrite -> "latest" by id order

    # 3) invoiced SMission -> mmission per car_num (one query)
    sm_mission_by_car = {}     # car_num -> mmission_id (latest invoiced)
    if car_nums:
        for sm in (SMission.objects
                   .filter(car_num__in=car_nums, receipt="Invoiced")
                   .values('car_num', 'mmission_id')
                   .order_by('id')):
            sm_mission_by_car[(sm['car_num'] or '').strip()] = sm['mmission_id']

    # build invoice_id -> cost center name (prefer mission-matched, else per-car fallback)
    cc_by_invoice = {}
    for vr in voucher_rows:
        inv_id = vr['invoice_id']
        if inv_id in cc_by_invoice:
            continue
        cn = vr['car_num'].strip()
        mmission_id = sm_mission_by_car.get(cn)
        name_ = pm_by_mission_car.get((mmission_id, cn)) if mmission_id is not None else None
        if not name_:
            name_ = pm_by_car.get(cn)
        if name_:
            cc_by_invoice[inv_id] = name_

    # ---- per-item vehicle number: items and vouchers are created 1:1 in the same
    #      order (see mobile invoice-creation loop), so pair them by id order. ----
    # vehicle car_num per invoice, ordered by voucher creation (id)
    chassis_lists = {}
    for v in (Vouchers.objects.filter(invoice_id__in=invoice_ids)
              .order_by('id').values('invoice_id', 'car_num')):
        chassis_lists.setdefault(v['invoice_id'], []).append((v['car_num'] or '').strip())

    # items grouped per invoice in id order (same order they were created)
    items_by_invoice = {}
    for it in (Items.objects.filter(number_id__in=invoice_ids)
               .order_by('id')
               .values('number_id', 'udinar', 'ufils', 'qty', 'description', 'adinar', 'afils')):
        items_by_invoice.setdefault(it['number_id'], []).append(it)

    # emit invoices oldest -> newest by date (then number, then id as tiebreakers)
    ordered_invoices = sorted(
        invoices,
        key=lambda inv: (inv.date or datetime.max.date(), inv.number or 0, inv.id)
    )

    rows = []
    for inv in ordered_invoices:
        inv_items = items_by_invoice.get(inv.id, [])
        inv_cars = chassis_lists.get(inv.id, [])
        for idx, it in enumerate(inv_items):
            # 1:1 pairing by position; blank if counts ever mismatch (never dump full list)
            chassis = inv_cars[idx] if idx < len(inv_cars) else ''
            rows.append({
                'udinar': it['udinar'], 'ufils': it['ufils'],
                'chassis': chassis,
                'cost_center': cc_by_invoice.get(inv.id, ''),
                'qty': it['qty'], 'description': it['description'],
                'invoice_number': inv.number,
                'adinar': it['adinar'], 'afils': it['afils'],
            })

    if not rows:
        return JsonResponse({'error': 'The selected invoices have no items.'}, status=400)

    # Reject exports that would exceed the template's item capacity (rows 19..10018).
    MAX_ITEMS = 10018 - 19 + 1          # = 10000, matches ITEM_START..LAST_ITEM_ROW
    if len(rows) > MAX_ITEMS:
        return JsonResponse(
            {'error': f'عدد البنود المحدد {len(rows)} يتجاوز الحد الأقصى {MAX_ITEMS}. '
                      f'الرجاء اختيار عدد أقل من الفواتير.'},
            status=400
        )

    # ---- totals (sum dinar/fils, carry 1000 fils -> 1 dinar) ----
    total_dinar = sum(int(inv.dinar or 0) for inv in invoices)
    total_fils = sum(int(inv.fils or 0) for inv in invoices)
    total_dinar += total_fils // 1000
    total_fils = total_fils % 1000

    # ---- customer name (same central-company rule as the single invoice) ----
    name = customer.name or ''
    if customer.notes and "الشرك" in customer.notes and "المركزي" in customer.notes and "تجار" in customer.notes:
        name = customer.notes

    car_numbers = ", ".join(dict.fromkeys([inv.car for inv in invoices if inv.car]))
    driver_names = ", ".join(dict.fromkeys([inv.driver.name for inv in invoices if inv.driver]))
    #invoice_numbers = ", ".join(str(inv.number) for inv in invoices)

    # ---- fill the template ----
    source_excel_path = os.path.join(settings.BASE_DIR, 'excel_templates', 'combined_invoice.xlsx')
    wb = openpyxl.load_workbook(source_excel_path)
    ws = wb.active

    # template anchors (new combined_invoice.xlsx layout)
    ITEM_START = 19
    LAST_ITEM_ROW = 10018

    #ws['A6'] = invoice_numbers
    ws['D7'] = "ذمم"
    ws['H9'] = datetime.now().strftime('%Y-%m-%d')
    ws['B11'] = name
    #ws['A13'] = car_numbers
    #ws['A15'] = customer.notes if customer.notes else ""

    next_row = ITEM_START
    for idx, r in enumerate(rows, start=ITEM_START):
        ws.cell(row=idx, column=1,  value=r['adinar'])           # B  unit price - fils
        ws.cell(row=idx, column=2,  value=r['afils'])          # A  unit price - dinar
        ws.cell(row=idx, column=3,  value=r['chassis'])         # C  chassis / vehicle number
        ws.cell(row=idx, column=4,  value=r['cost_center'])     # D  cost / service center
        #ws.cell(row=idx, column=5,  value=r['qty'])             # E  quantity
        ws.cell(row=idx, column=6,  value=r['description'])     # F..I  description (merged)
        ws.cell(row=idx, column=10, value=r['invoice_number'])  # J  invoice number (NEW)
        #ws.cell(row=idx, column=11, value=r['adinar'])          # K  total price - dinar
        #ws.cell(row=idx, column=12, value=r['afils'])           # L  total price - fils
        next_row = idx + 1

    # hide the unused item rows between the last record and the totals/title block
    for hide_r in range(next_row, LAST_ITEM_ROW + 1):
        ws.row_dimensions[hide_r].hidden = True

    # fixed width for chassis (C); auto-fit cost-center (D)
    ws.column_dimensions['C'].width = 44
    ws.column_dimensions['F'].width = 12
    ws.column_dimensions['G'].width = 17
    ws.column_dimensions['H'].width = 19
    ws.column_dimensions['I'].width = 12

    max_len = len(str(ws['D17'].value or ''))
    for rr in range(ITEM_START, next_row):
        val = ws.cell(row=rr, column=4).value
        if val is not None:
            max_len = max(max_len, len(str(val)))
    ws.column_dimensions['D'].width = max_len + 2

    # totals + footer (totals shifted one column right: K/L)
    ws['A10020'] = total_dinar
    ws['B10020'] = total_fils
    ws['C10019'] = amount_to_arabic_words(total_dinar, total_fils)
    #ws['G2034'] = driver_names

    # Approximate: only force the footer to a new page if it wouldn't fit under
    # the last item on the current page. Tune ROWS_PER_PAGE / FOOTER_ROWS to taste.
    ROWS_PER_PAGE = 25      # item rows that fit on a continuation page
    FOOTER_ROWS = 6         # rows the totals + signature block occupies
    items_on_last_page = (len(rows)) % ROWS_PER_PAGE
    # if the last page is too full to also hold the footer, push footer down
    if items_on_last_page == 0 or items_on_last_page > (ROWS_PER_PAGE - FOOTER_ROWS):
        from openpyxl.worksheet.pagebreak import Break
        ws.row_breaks.append(Break(id=next_row - 1))
    # else: no break — footer flows right after the last item on the same page

    # ---- save + convert to PDF via LibreOffice ----
    output_excel_path = os.path.join(settings.MEDIA_ROOT, f'combined_invoice_{customer.id}.xlsx')
    wb.save(output_excel_path)

    try:
        output_pdf_path = os.path.splitext(output_excel_path)[0] + '.pdf'
        subprocess.run(["pkill", "-f", "soffice.bin"], check=False)
        subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf", output_excel_path,
             '--outdir', os.path.dirname(output_pdf_path)],
            check=True
        )
        if os.path.exists(output_pdf_path):
            with open(output_pdf_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="Combined Invoice {customer.id}.pdf"'
            for p in (output_excel_path, output_pdf_path):
                if os.path.exists(p):
                    os.remove(p)
            return response
        raise Http404("PDF file not found")
    except Exception as e:
        print("Error:", e)
        return JsonResponse({'error': f'PDF conversion failed: {str(e)}'}, status=500)


def customer_activities(request, id):
    from recipt_vouchers.models import Vouchers   # transport vouchers
    from django.db.models import Count

    amman_tz = pytz.timezone('Asia/Amman')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    car = (request.GET.get('car') or '').strip()

    # ---------- ACTIVITY ----------
    invoices = Invoices.objects.filter(require_id__id=id, type="ذمم")
    treasury = Treasury.objects.filter(customer__id=id)
    if date_from and date_to:
        invoices = invoices.filter(date__range=(date_from, date_to))
        treasury = treasury.filter(created_at__date__range=(date_from, date_to))
    if car:
        invoices = invoices.filter(car__icontains=car)

    entries = []
    for inv in invoices.values('number', 'tamount', 'created_at'):
        entries.append({
            'account': 'Created invoice',
            'number': inv['number'],
            'amount': str(inv['tamount']),
            'created_at': localtime(inv['created_at'], amman_tz).isoformat(),
        })
    # treasury (payments) aren't vehicle-specific; include them only when not filtering by car
    if not car:
        for t in treasury.values('number', 'amount', 'created_at'):
            entries.append({
                'account': 'Paid to treasury',
                'number': t['number'],
                'amount': str(t['amount']),
                'created_at': localtime(t['created_at'], amman_tz).isoformat(),
            })
    entries.sort(key=lambda e: e['created_at'])

    # ---------- CUSTOMER VEHICLES + transport-process count ----------
    # Count vouchers (transport processes) per vehicle for this customer,
    # within the same date window (filtered on the delivery time) and car filter.
    vouchers = Vouchers.objects.filter(car_owner__id=id)
    if date_from and date_to:
        vouchers = vouchers.filter(receipt_to_time__date__range=(date_from, date_to))
    if car:
        vouchers = vouchers.filter(car_num__icontains=car)

    # transports per (car_num, car_type) group
    counts = {}
    for row in vouchers.values('car_num', 'car_type').annotate(n=Count('id')):
        counts[(row['car_num'], row['car_type'])] = row['n']

    # distinct vehicle rows (one per car_num/car_type), with details + count
    seen = set()
    vehicles = []
    for v in vouchers.values('car_num', 'car_type', 'car_mark', 'car_color').order_by('car_num'):
        key = (v['car_num'], v['car_type'])
        if key in seen:
            continue
        seen.add(key)
        vehicles.append({
            'car_type': v['car_type'] or '',
            'car_num': v['car_num'] or '',
            'car_mark': v['car_mark'] or '',
            'car_color': v['car_color'] or '',
            'transports': counts.get(key, 0),
        })

    return JsonResponse({'entries': entries, 'vehicles': vehicles}, safe=False)

def update_customer_balance(customer_id):
    customer = get_object_or_404(Customers, id=customer_id)
    total_invoiced = Invoices.objects.filter(Q(require_id__id=customer_id) & Q(type="ذمم")).aggregate(Sum('tamount'))['tamount__sum'] or 0
    total_treasury = Treasury.objects.filter(customer__id=customer_id).aggregate(Sum('amount'))['amount__sum'] or 0
    customer.balance = total_invoiced - total_treasury
    customer.save()


@login_required
def customer_info_report(request):
    from . import customer_reports as cr
    qs = Customers.objects.all()

    query = (request.GET.get('query') or '').strip()
    if query:
        qs = qs.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(mail__icontains=query) |
            Q(address__icontains=query)
        )

    # match the page's payment radio (option1=ذمم, option2=نقدي; option0/مدين=all)
    option = request.GET.get('inlineRadioOptions')
    if option == 'option1':
        qs = qs.filter(payment='ذمم')
    elif option == 'option2':
        qs = qs.filter(payment='نقدي')

    customers = list(
        qs.order_by('name').values('name', 'phone', 'mail', 'address', 'payment', 'balance')
    )
    today = localtime(now(), pytz.timezone('Asia/Amman')).strftime('%Y-%m-%d')
    buf = io.BytesIO()
    cr.build_customer_info_pdf(buf, customers, generated_on=today)
    buf.seek(0)
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Customers_Info.pdf"'
    return response