"""
Driver overtime calculation.

Source of truth: recipt_vouchers.Vouchers
    begin = receipt_from_time  (driver received the car)
    end   = receipt_to_time    (driver delivered the car)

For every driver and every local (Asia/Amman) day:
  1. the day's work span = first voucher begin  ->  last voucher end
     (gaps between vouchers are still work: driving back, waiting for the next car)
     A night trip that ends before the next day's work begins stays on the day it began;
     a voucher that starts after midnight while that trip is still running joins it.
     LONG vouchers (still open when the next day's work begins, e.g. a car kept for days)
     are NOT continuous work: only the receipt moment counts on its day and only the
     delivery moment counts on the delivery day. Days in between and their work hours
     are never counted from them.
  2. Weekly off day  -> the whole span is overtime:  hours x off_day_multiplier
     Normal work day -> before = first begin .. work_start  (only if count_before)
                        after  = work_end    .. last end    (only if count_after)
  3. a part shorter than grace_minutes is ignored
  4. weighted hours = before*before_mult + after*after_mult + off_day*off_day_mult
     (hours rounded to 2 decimals first, then weighted rounded half-up, same as Excel)

Vouchers that are still open (no receipt_to_time) are not counted, only reported.
"""
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

import pytz

AMMAN_TZ = pytz.timezone('Asia/Amman')
TWO_PLACES = Decimal('0.01')
ZERO = Decimal('0.00')

# (python weekday number, name) in Jordan's week order: Sunday first
WEEKDAY_CHOICES = [(6, 'Sunday'), (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
                   (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday')]
WEEKDAY_NAMES = dict(WEEKDAY_CHOICES)


# --------------------------------------------------------------------------- helpers
def _local_at(d, t):
    return AMMAN_TZ.localize(datetime.combine(d, t))


def _dec(value):
    return Decimal(str(value or 0))


def _hours(seconds):
    return (Decimal(str(seconds)) / Decimal(3600)).quantize(TWO_PLACES, ROUND_HALF_UP)


def parse_off_days(value):
    """'4,5' -> {4, 5}   (python weekday numbers, Monday = 0)"""
    if isinstance(value, (set, list, tuple)):
        items = value
    else:
        items = str(value or '').split(',')
    return {int(x) for x in items if str(x).strip().isdigit() and 0 <= int(x) <= 6}


def off_day_names(off_days):
    return [name for num, name in WEEKDAY_CHOICES if num in off_days]


def settings_to_dict(s):
    """Accepts an OvertimeSettings instance and returns plain values."""
    return {
        'work_start': s.work_start,
        'work_end': s.work_end,
        'count_before': bool(s.count_before),
        'before_multiplier': _dec(s.before_multiplier),
        'count_after': bool(s.count_after),
        'after_multiplier': _dec(s.after_multiplier),
        'off_days': parse_off_days(s.off_days),
        'off_day_multiplier': _dec(s.off_day_multiplier),
        'grace_minutes': int(s.grace_minutes or 0),
    }


# --------------------------------------------------------------------------- core (no Django)
def compute_overtime(entries, cfg, date_from, date_to):
    """
    entries : iterable of (driver_name, voucher_id, start_dt, end_dt) with aware datetimes.
              Include the day before date_from so night trips are not double counted.
    cfg     : dict from settings_to_dict()
    returns : {'rows': [...], 'drivers': [...], 'totals': {...}}
    """
    bm, am, om = _dec(cfg['before_multiplier']), _dec(cfg['after_multiplier']), _dec(cfg['off_day_multiplier'])
    off_days = parse_off_days(cfg.get('off_days'))
    grace_sec = int(cfg.get('grace_minutes') or 0) * 60

    by_driver = defaultdict(list)
    for name, vid, start, end in entries:
        if not name or not start or not end or end <= start:
            continue
        by_driver[name.strip()].append((start.astimezone(AMMAN_TZ), end.astimezone(AMMAN_TZ), vid))

    one_day = timedelta(days=1)
    rows, drivers = [], []
    for name in sorted(by_driver):
        # shifts: {work day: {'first', 'last', 'vouchers', 'items'}}
        #   items = [(voucher_id, role)]  role: 'trip' | 'begin' (long, receipt only) | 'end' (long, delivery only)
        shifts = {}

        def touch(moment_day, a, b, vid, role):
            prev = shifts.get(moment_day - one_day)
            day = moment_day - one_day if prev and a <= prev['last'] else moment_day   # inside last night's trip
            sh = shifts.get(day)
            if sh is None:
                sh = shifts[day] = {'first': a, 'last': b, 'vouchers': 0, 'items': []}
            else:
                sh['first'], sh['last'] = min(sh['first'], a), max(sh['last'], b)
            if role != 'end':
                sh['vouchers'] += 1
            sh['items'].append((vid, role))
            return day

        for s, e, vid in sorted(by_driver[name], key=lambda x: x[0]):
            prev = shifts.get(s.date() - one_day)
            day = s.date() - one_day if prev and s <= prev['last'] else s.date()
            if e <= _local_at(day + one_day, cfg['work_start']):
                touch(s.date(), s, e, vid, 'trip')            # continuous trip (same day or night trip)
            else:
                touch(s.date(), s, s, vid, 'begin')           # long voucher: receipt moment only
                touch(e.date(), e, e, vid, 'end')             # ... and delivery moment only

        drv = {'driver': name, 'work_days': 0, 'overtime_days': 0, 'off_days_worked': 0, 'vouchers': 0,
               'before_hours': ZERO, 'after_hours': ZERO, 'off_day_hours': ZERO,
               'total_hours': ZERO, 'weighted_hours': ZERO}

        for d in sorted(shifts):
            shift = shifts[d]
            first, last = shift['first'], shift['last']
            if not (date_from <= d <= date_to):
                continue
            drv['work_days'] += 1
            drv['vouchers'] += shift['vouchers']

            is_off = d.weekday() in off_days
            before_sec = after_sec = off_sec = 0.0
            if is_off:
                off_sec = (last - first).total_seconds()
                if off_sec < grace_sec:
                    off_sec = 0.0
            else:
                if cfg['count_before']:
                    ws = _local_at(d, cfg['work_start'])
                    if first < ws:
                        before_sec = (min(last, ws) - first).total_seconds()
                        if before_sec < grace_sec:
                            before_sec = 0.0
                if cfg['count_after']:
                    we = _local_at(d, cfg['work_end'])
                    if last > we:
                        after_sec = (last - max(first, we)).total_seconds()
                        if after_sec < grace_sec:
                            after_sec = 0.0

            bh, ah, oh = _hours(before_sec), _hours(after_sec), _hours(off_sec)
            if not (bh or ah or oh):
                continue
            weighted = (bh * bm + ah * am + oh * om).quantize(TWO_PLACES, ROUND_HALF_UP)

            rows.append({
                'driver': name, 'date': d, 'is_off_day': is_off,
                'first_start': first, 'last_end': last, 'vouchers': shift['vouchers'],
                'voucher_items': shift['items'],
                'before_hours': bh, 'after_hours': ah, 'off_day_hours': oh,
                'total_hours': bh + ah + oh, 'weighted_hours': weighted,
            })
            drv['overtime_days'] += 1
            drv['off_days_worked'] += 1 if is_off else 0
            drv['before_hours'] += bh
            drv['after_hours'] += ah
            drv['off_day_hours'] += oh
            drv['weighted_hours'] += weighted

        drv['total_hours'] = drv['before_hours'] + drv['after_hours'] + drv['off_day_hours']
        drivers.append(drv)

    totals = {k: sum((x[k] for x in drivers), ZERO)
              for k in ('before_hours', 'after_hours', 'off_day_hours', 'total_hours', 'weighted_hours')}
    totals.update({k: sum(x[k] for x in drivers)
                   for k in ('work_days', 'overtime_days', 'off_days_worked', 'vouchers')})
    return {'rows': rows, 'drivers': drivers, 'totals': totals}


# --------------------------------------------------------------------------- Django side
def build_overtime_report(settings_obj, date_from, date_to, driver_names=None):
    """Fetches vouchers for the period and runs compute_overtime()."""
    from recipt_vouchers.models import Vouchers

    start = _local_at(date_from, time.min)
    end = _local_at(date_to + timedelta(days=1), time.min)

    base = Vouchers.objects.exclude(driver_name__isnull=True).exclude(driver_name='')
    if driver_names:
        base = base.filter(driver_name__in=driver_names)

    # every voucher that touches the range (a long voucher that began earlier can still
    # be delivered inside it), plus the day before so night trips are recognised
    closed = (base.filter(receipt_from_time__isnull=False, receipt_to_time__isnull=False,
                          receipt_from_time__lt=end,
                          receipt_to_time__gte=start - timedelta(days=1))
                  .values_list('driver_name', 'id', 'receipt_from_time', 'receipt_to_time'))

    report = compute_overtime(closed, settings_to_dict(settings_obj), date_from, date_to)

    # voucher details for the "by days" Excel sheet
    ids = sorted({vid for row in report['rows'] for vid, _ in row['voucher_items']})
    details = {}
    for i in range(0, len(ids), 500):
        for v in Vouchers.objects.filter(id__in=ids[i:i + 500]).values(
                'id', 'number', 'car_type', 'car_mark', 'car_num', 'car_color', 'car_owner__name',
                'receipt_from_location', 'receipt_from_time', 'receipt_to_location', 'receipt_to_time'):
            details[v['id']] = v
    report['voucher_details'] = details
    report['open_vouchers'] = base.filter(receipt_from_time__range=(start, end),
                                          receipt_to_time__isnull=True).count()
    return report
