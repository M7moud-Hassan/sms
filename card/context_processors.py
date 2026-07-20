import json

from django.conf import settings


def firebase_config(request):
    return {
        'firebase_web_config': settings.FIREBASE_WEB_CONFIG,
        'firebase_web_config_json': json.dumps(settings.FIREBASE_WEB_CONFIG),
        'firebase_vapid_key': settings.FIREBASE_VAPID_KEY,
    }
