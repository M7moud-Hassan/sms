from django.shortcuts import get_object_or_404
from django.db.models import Sum
from .models import Invoices, Items
from drivers.models import Drivers, Treasury
from customers.models import Customers, Treasury as Tr

# Create your views here.
num2words = {1: 'واحد', 2: 'إثنان', 3: 'ثلاثة', 4: 'أربعة', 5: 'خمسة', 6: 'ستة', 7: 'سبعة', 8: 'ثمانية', 9: 'تسعة', 10: 'عشرة', \
             11: 'إحدى عشر', 12: 'إثنا عشر', 13: 'ثلاثة عشر', 14: 'أربعة عشر', 15: 'خمسة عشر', 16: 'ستة عشر', 17: 'سبعة عشر', 18: 'ثمانية عشر', 19: 'تسعة عشر', 20: 'عشرون', \
             21: 'واحد وعشرون', 22: 'إثنان وعشرون', 23: 'ثلاثة وعشرون', 24: 'أربعة وعشرون', 25: 'خمسة وعشرون', 26: 'ستة وعشرون', 27: 'سبعة وعشرون', 28: 'ثمانية وعشرون', 29: 'تسعة وعشرون', 30: 'ثلاثون', \
             31: 'واحد وثلاثون', 32: 'إثنان وثلاثون', 33: 'ثلاثة وثلاثون', 34: 'أربعة وثلاثون', 35: 'خمسة وثلاثون', 36: 'ستة وثلاثون', 37: 'سبعة وثلاثون', 38: 'ثمانية وثلاثون', 39: 'تسعة وثلاثون', 40: 'أربعون', \
             41: 'واحد وأربعون', 42: 'إثنان وأربعون', 43: 'ثلاثة وأربعون', 44: 'أربعة وأبعون', 45: 'خمسة وأربعون', 46: 'ستة وأربعون', 47: 'سبعة وأربعون', 48: 'ثمانية وأربعون', 49: 'تسعة وأربعون', 50: 'خمسون', \
             51: 'واحد وخمسون', 52: 'إثنان وخمسون', 53: 'ثلاثة وخمسون', 54: 'أربعة وخمسون', 55: 'خمسة وخمسون', 56: 'ستة وخمسون', 57: 'سبعة وخمسون', 58: 'ثمانية وخمسون', 59: 'تسعة وخمسون', 60: 'ستون', \
             61: 'واحد وستون', 62: 'إثنان وستون', 63: 'ثلاثة وستون', 64: 'أربعة وستون', 65: 'خمسة وستون', 66: 'ستة وستون', 67: 'سبعة وستون', 68: 'ثمانية وستون', 69: 'تسعة وستون', 70: 'سبعون', \
             71: 'واحد وسبعون', 72: 'إثنان وسبعون', 73: 'ثلاثة وسبعون', 74: 'أربعة وسبعون', 75: 'خمسة وسبعون', 76: 'ستة وسبعون', 77: 'سبعة وسبعون', 78: 'ثمانية وسبعون', 79: 'تسعة وسبعون', 80: 'ثمانون', \
             81: 'واحد وثمانون', 82: 'إثنان وثمانون', 83: 'ثلاثة وثمانون', 84: 'أربعة وثمانون', 85: 'خمسة وثمانون', 86: 'ستة وثمانون', 87: 'سبعة وثمانون', 88: 'ثمانية وثمانون', 89: 'تسعة وثمانون', 90: 'تسعون', \
             91: 'واحد وتسعون', 92: 'إثنان وتسعون', 93: 'ثلاثة وتسعون', 94: 'أربعة وتسعون', 95: 'خمسة وتسعون', 96: 'ستة وتسعون', 97: 'سبعة وتسعون', 98: 'ثمانية وتسعون', 99: 'تسعة وتسعون'}
def n2w(n):
    try:
        return num2words[n]
    except:
        try:
            return num2words[n - n % 10] + num2words[n % 10].lower()
        except:
            try:
                if (int(n) > 0 and int(n) <= 99):
                    w = ''
                    w = n2w(int(n))
                    return w
                elif (int(n) >= 100 and int(n) <= 999):
                    w = ''
                    if int(n) < 200:
                        w = 'مائة'
                    elif int(n) < 300:
                        w = 'مائتان'
                    elif int(n) < 400:
                        w = 'ثلاثمائة'
                    elif int(n) < 500:
                        w = 'أربعمائة'
                    elif int(n) < 600:
                        w = 'خمسمائة'
                    elif int(n) < 700:
                        w = 'ستمائة'
                    elif int(n) < 800:
                        w = 'سبعمائة'
                    elif int(n) < 900:
                        w = 'ثمانمائة'
                    else:
                        w = 'تسعمائة'
                    n = n - (int(n / 100) * 100)
                    if (int(n) > 0):
                        w += ' و ' + n2w(int(n))
                    return w
                elif (int(n) >= 1000 and int(n) < 1000000):
                    w = ''
                    if int(n) < 2000:
                        w = 'ألف'
                    elif int(n) < 3000:
                        if int(n) == 2000:
                            w = 'ألفي'
                        else:
                            w = 'ألفان'
                    elif int(n) < 11000:
                        w += n2w(int(n / 1000)) + ' آلاف'
                    else:
                        w += n2w(int(n / 1000)) + ' ألف'
                    n -= int((n / 1000)) * 1000
                    if (int(n) > 0 and int(n) < 100):
                        w += ' و ' + n2w(int(n))
                    if (int(n) >= 100):
                        if int(n) < 200:
                            w += ' و مائة'
                        elif int(n) < 300:
                            w += ' و مائتان'
                        elif int(n) < 400:
                            w += ' و ثلاثمائة'
                        elif int(n) < 500:
                            w += ' و أربعمائة'
                        elif int(n) < 600:
                            w += ' و خمسمائة'
                        elif int(n) < 700:
                            w += ' و ستمائة'
                        elif int(n) < 800:
                            w += ' و سبعمائة'
                        elif int(n) < 900:
                            w += ' و ثمانمائة'
                        else:
                            w += ' و تسعمائة'
                        n -= (int(n / 100) * 100)
                        if (int(n) > 0):
                            w += ' و ' + n2w(int(n))
                elif (int(n) >= 1000000):
                    w = ''
                    if int(n) < 2000000:
                        w = 'مليون'
                    else:
                        w += n2w(int(n / 1000000)) + ' مليون '
                    n -= int((n / 1000000)) * 1000000
                    if (int(n) >= 1000):
                        if int(n) < 2000:
                            w += ' و ألف'
                        elif int(n) < 3000:
                            if int(n) == 2000:
                                w += ' و ألفي'
                            else:
                                w += ' و ألفان'
                        elif int(n) < 11000:
                            w += n2w(int(n / 1000)) + ' آلاف'
                        else:
                            w += n2w(int(n / 1000)) + ' ألف'
                        n = n - int((n / 1000)) * 1000
                        if (int(n) > 0 and int(n) < 100):
                            w = w + ' و ' + n2w(int(n))
                        if (int(n) >= 100):
                            if int(n) < 200:
                                w += ' و مائة'
                            elif int(n) < 300:
                                w += ' و مائتان'
                            elif int(n) < 400:
                                w += ' و ثلاثمائة'
                            elif int(n) < 500:
                                w += ' و أربعمائة'
                            elif int(n) < 600:
                                w += ' و خمسمائة'
                            elif int(n) < 700:
                                w += ' و ستمائة'
                            elif int(n) < 800:
                                w += ' و سبعمائة'
                            elif int(n) < 900:
                                w += ' و ثمانمائة'
                            else:
                                w += ' و تسعمائة'
                            n -= (int(n / 100) * 100)
                            if (int(n) > 0):
                                w += ' و ' + n2w(int(n))
                return w
            except KeyError:
                return 'Ayyao'

def update_invoice(invoice_number):
    invoice = get_object_or_404(Invoices, id=invoice_number)
    total_dinar = Items.objects.filter(number__id=invoice_number).aggregate(Sum('adinar'))['adinar__sum'] or 0
    total_fils = Items.objects.filter(number__id=invoice_number).aggregate(Sum('afils'))['afils__sum'] or 0
    if total_fils >= 100:
        diff = int(total_fils/100)
        total_dinar += diff
        total_fils -= diff * 100
    # Calculate total amount
    invoice.tamount = total_dinar + total_fils / 100.0  # Ensure floating-point division
    invoice.dinar = int(invoice.tamount)  # Dinar part
    invoice.fils = int(round((invoice.tamount - invoice.dinar) * 100))  # Fils part (rounded)
    if total_fils > 0:
        invoice.samount = "فقط وقدره " + n2w(total_dinar) + ' دينار و ' + n2w(total_fils) + ' فلس لا غير'
    elif total_dinar > 0:
        invoice.samount = "فقط وقدره " + n2w(total_dinar) + ' دينار لا غير'
    driver_paid = Treasury.objects.filter(invoice__id=invoice_number).aggregate(Sum('amount'))['amount__sum'] or 0
    customer_paid = Tr.objects.filter(invoice__id=invoice_number).aggregate(Sum('amount'))['amount__sum'] or 0
    invoice.driver_paid = driver_paid
    invoice.customer_paid = customer_paid
    invoice.save()