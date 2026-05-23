from celery import shared_task
from django.utils import timezone
from django.db.models import Q
import logging
from .models import Card

logger = logging.getLogger(__name__)

@shared_task
def deactivate_expired_cards():
    """
    Deactivate all cards where end_at <= today and is_active=True.
    """
    today = timezone.now().date()
    # Use __date lookup to compare only the date part
    expired_cards = Card.objects.filter(end_at__date__lte=today, is_active=True)
    count = expired_cards.count()
    
    if count:
        expired_cards.update(is_active=False)
        logger.info(f'Deactivated {count} expired card(s).')
        return f'Deactivated {count} expired card(s).'
    else:
        logger.info('No expired cards found.')
        return 'No expired cards found.'