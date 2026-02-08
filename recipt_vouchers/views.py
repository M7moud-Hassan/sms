from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Max, Q
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, FileResponse
from django.urls import reverse
import os
import openpyxl
from django.conf import settings
import subprocess
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
import pytz
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.utils.timezone import make_aware, localtime
from django.utils.dateparse import parse_date
from .forms import SearchForm
from .models import Vouchers, Attachments
from drivers.models import SMission, MMission

def index(request):
    adjusted_vouchers = MMission.objects.filter(count__gt=0)
    number_of_vehicles = adjusted_vouchers.aggregate(Sum('count'))['count__sum'] or 0
    form = SearchForm(request.GET)
    result = None
    start_date = None
    end_date = None
    options = "option0"
    # Ensure amman_tz is always defined
    amman_tz = pytz.timezone('Asia/Amman')
    if "search" in request.GET:
        result = "ok"
        start_date = request.GET['start_date']
        end_date = request.GET['end_date']
        vouchers = Vouchers.objects.all()
        if request.GET['inlineRadioOptions'] == "option1":
            vouchers = Vouchers.objects.filter(Q(recipient_to_name__isnull=True) & Q(recipient_from_name__isnull=False)).order_by('receipt_from_time')
            options = "option1"
        elif request.GET['inlineRadioOptions'] == "option2":
            vouchers = Vouchers.objects.filter(Q(recipient_to_name__isnull=False) & Q(invoice__exported__isnull=True)).order_by('receipt_to_time')
            options = "option2"
        elif request.GET['inlineRadioOptions'] == "option3":
            vouchers = Vouchers.objects.filter(Q(invoice__exported__isnull=False) & Q(invoice__date__range=(start_date, end_date))).order_by('receipt_to_time')
            options = "option3"
        if form.is_valid() and (options == "option1" or options == "option2" or options == "option3"):
            query = form.cleaned_data['query']
            vouchers = vouchers.filter(
                Q(driver_name__icontains=query) |
                Q(car_num__icontains=query) |
                Q(car_owner__name__icontains=query)  # Corrected here
            )
    if options == "option1" or options == "option2" or options == "option3":
        # Debugging: Check the query
        vouchers = vouchers.prefetch_related('attachments_set')
        adjusted_vouchers = []
        for voucher in vouchers:
            voucher.receipt_from_time = localtime(voucher.receipt_from_time, amman_tz)
            voucher.receipt_to_time = localtime(voucher.receipt_to_time, amman_tz)
            voucher.adjusted_receipt_from_time = voucher.receipt_from_time
            voucher.adjusted_receipt_to_time = voucher.receipt_to_time
            time_diff = voucher.receipt_from_time.utcoffset().total_seconds() / 3600
            if voucher.receipt_from_time:
                voucher.adjusted_receipt_from_time += timedelta(hours=time_diff)
            if voucher.receipt_to_time:
                voucher.adjusted_receipt_to_time += timedelta(hours=time_diff)
            adjusted_vouchers.append(voucher)
        number_of_vehicles = vouchers.count()
    context = {
        'active_tab': 'recipt_vouchers',
        'vouchers': adjusted_vouchers,
        'number_of_vehicles': number_of_vehicles,
        'form': form,
        'result': result,
        'start_date': start_date,
        'end_date': end_date,
        'options': options,
    }
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('recipt_vouchers_index')
        else:
            messages.success(request, "There was an error for username or password...")
            return redirect('recipt_vouchers_index')
    username = request.user.username
    if 'jobbox' in username:
        return redirect('pmissions_index')
    else:
        return render(request, "recipt_vouchers/index.html", context)

def fetch_attachments(request):
    id = request.GET.get('id')
    rattachments = Attachments.objects.filter(Q(voucher__id=id) & Q(page="Received"))
    rattachments_list = [{'strike_chart_url': request.build_absolute_uri(rattachment.strike_chart.url)} for rattachment in rattachments]
    dattachments = Attachments.objects.filter(Q(voucher__id=id) & Q(page="Delivered"))
    dattachments_list = [{'strike_chart_url': request.build_absolute_uri(dattachment.strike_chart.url)} for dattachment in dattachments]
    return JsonResponse({'rattachments': rattachments_list, 'dattachments': dattachments_list})

