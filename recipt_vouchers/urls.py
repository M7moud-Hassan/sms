from django.urls import path
from . import views

urlpatterns = [
    path('fetch_attachments/', views.fetch_attachments, name='fetch_attachments'),
    path('', views.index, name="recipt_vouchers_index"),
]






