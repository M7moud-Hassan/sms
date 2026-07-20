import logging
import os

import firebase_admin
from django.conf import settings
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

_app = None
_app_init_failed = False


def _get_app():
    """Lazily initialize the Firebase Admin app from the configured service
    account file. Returns None (and logs once) if it isn't configured yet,
    so the rest of the app keeps working before Firebase is set up."""
    global _app, _app_init_failed
    if _app is not None:
        return _app
    if _app_init_failed:
        return None

    cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
    if not cred_path or not os.path.exists(cred_path):
        _app_init_failed = True
        logger.warning("Firebase not configured: FIREBASE_CREDENTIALS_PATH (%s) not found.", cred_path)
        return None

    try:
        cred = credentials.Certificate(cred_path)
        _app = firebase_admin.initialize_app(cred)
    except Exception:
        _app_init_failed = True
        logger.exception("Failed to initialize Firebase Admin SDK.")
        return None
    return _app


def send_push(tokens, title, body, data=None, icon='/static/image/logo.png'):
    """Send a web-push notification to one or more FCM registration tokens.
    No-ops quietly if Firebase isn't configured yet. Prunes tokens that FCM
    reports as no-longer-registered so the token table stays clean."""
    if isinstance(tokens, str):
        tokens = [tokens]
    tokens = [t for t in tokens if t]
    if not tokens:
        return

    app = _get_app()
    if app is None:
        return

    notification = messaging.Notification(title=title, body=body)
    str_data = {k: str(v) for k, v in (data or {}).items()}
    messages = [
        messaging.Message(
            notification=notification,
            data=str_data,
            token=token,
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    title=title,
                    body=body,
                    icon=icon,
                    require_interaction=True,
                ),
                fcm_options=messaging.WebpushFCMOptions(),
            ),
        )
        for token in tokens
    ]

    try:
        response = messaging.send_each(messages, app=app)
    except Exception:
        logger.exception("Firebase push send failed for %d token(s).", len(tokens))
        return

    invalid_tokens = []
    for token, result in zip(tokens, response.responses):
        if not result.success:
            if isinstance(result.exception, messaging.UnregisteredError):
                invalid_tokens.append(token)
            else:
                logger.warning("FCM send failed for a token: %s", result.exception)

    if invalid_tokens:
        from .models import FCMToken
        FCMToken.objects.filter(token__in=invalid_tokens).delete()
