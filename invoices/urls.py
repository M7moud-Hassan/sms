from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="invoices_index"),
    path('edit/<int:id>/', views.edit_invoice, name="edit_invoice"),
    path('<int:number>/', views.invoice_details, name="invoice_details"),
    path('<int:number>/export/', views.export_invoice, name="export_invoice"),
    path('<int:number>/send/', views.send_invoice, name="send_invoice"),
    path('add_invitem/', views.add_invitem, name="add_invitem"),
    path('edit_invitem/<int:id>/', views.edit_invitem, name="edit_invitem"),
    path('delete_invitem/<int:id>/', views.delete_invitem, name="delete_invitem"),
]








