"""
ASGI config for project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""
import os
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import drivers.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

#application = get_asgi_application()
# Keep the HTTP ASGI application to handle traditional HTTP requests
#django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),  # Keep this line to handle regular HTTP requests
    "websocket": AuthMiddlewareStack(
        URLRouter(
            drivers.routing.websocket_urlpatterns  # Use your actual routing configuration
        )
    ),
})