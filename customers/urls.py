from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="customers_index"),
    path('get_invoices/', views.get_invoices, name='cget_invoices'),
    path('get_invoice_details/', views.get_invoice_details, name='cget_invoice_details'),
    path('add/', views.add_customer, name='add_customer'),
    path('add_treasury/', views.add_treasury, name='add_ctreasury'),
    path('edit_treasury/<int:id>/', views.edit_treasury, name="edit_ctreasury"),
    path('delete_treasury/<int:id>/', views.delete_treasury, name="delete_ctreasury"),
    path('export/<int:id>/<str:date_from>/<str:date_to>/', views.export_treasury, name='export_ctreasury'),
    path('edit/<int:id>/', views.edit_customer, name='edit_customer'),
    path('details/<int:id>/', views.customer_details, name='customer_details'),
    path('add_attachment/', views.add_attachment, name='add_attachment'),
    path('edit_attachment/<int:id>/', views.edit_attachment, name='edit_attachment'),
    path('delete_attachment/<int:id>/', views.delete_attachment, name='delete_attachment'),
    path('balance/<int:id>/', views.customer_balance, name="customer_balance"),
    path('filter/<int:id>/', views.filter_invoices, name='cfilter_invoices'),
]






