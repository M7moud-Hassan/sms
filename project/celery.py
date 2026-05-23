# your_project/celery.py
import os
from celery import Celery

# تعيين متغير البيئة لمشروع Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

app = Celery('your_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()