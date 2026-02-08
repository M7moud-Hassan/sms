from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.index, name="mobile_index"),
    path('<str:vehicle_number>/', views.logout, name="logout"),
    path('customers/<str:phone>/', views.get_customer, name="get_customer"),
    path('customers/<str:phone>/page1/<int:number>/', views.page1_2, name="page_1_2"),
    path('customers/<str:phone>/<int:id>/page1/', views.page1_1, name="page_1_1"),
    path('page2/<int:number>/', views.page2_1, name="page2_1"),
    path('page2/<int:number>/attachments/', views.page2_2, name="page2_2"),
    path('page3/<int:number>/', views.page3_1, name="page_3_1"),
    path('page3/<int:number>/attachments/', views.page3_2, name="page_3_2"),
    path('page3/<str:phone>/<str:driver_name>/', views.page3_3, name="page_3_3"),
    path('page3/<str:driver_name>/', views.page3, name="page_3"),
    path('customers/<str:phone>/page4/', views.page4, name="page4"),
    path('customers/<str:phone>/page4/<str:driver_name>/<str:vehicle_number>/', views.get_invoices, name="get_invoices"),
    path('customers/<str:phone>/page4/<str:driver_name>/<str:vehicle_number>/export/', views.export_invoice, name="mexport_invoice"),
    path('customers/<str:phone>/page4/<str:driver_name>/<str:vehicle_number>/share/', views.share_invoice, name="share_invoice"),
    path('customers/<str:phone>/page4/<str:driver_name>/<str:vehicle_number>/items/', views.get_items, name="get_items"),
    path('customers/<str:phone>/page4/<str:driver_name>/<str:vehicle_number>/items/<int:pk>/', views.put_item, name="put_item"),
    path('todo/<int:id>/', views.get_sub_missions, name="get_sub_missions"),
    path('todo/<str:driver_name>/', views.get_missions, name="get_missions"),
    path('oil/<str:vehicle_number>/', views.get_alerts, name="get_alerts"),
    path('oil/<str:driver_name>/<str:vehicle_number>/', views.get_oil, name="get_oil"),
    path('fuel/<str:driver_name>/<str:vehicle_number>/', views.get_fuel, name="get_fuel"),
]
