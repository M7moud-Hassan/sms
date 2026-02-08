from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="drivers_index"),
    path('my_view/', views.my_view, name="my_view"),
    path('get_invoices/', views.get_invoices, name='get_invoices'),
    path('get_invoice_details/', views.get_invoice_details, name='get_invoice_details'),
    path('add/', views.add_driver, name="add_driver"),
    path('edit/<int:id>/', views.edit_driver, name="edit_driver"),
    path('delete/<int:id>/', views.delete_driver, name="delete_driver"),
    path('balance/<int:id>/', views.driver_balance, name="driver_balance"),
    path('add_treasury/', views.add_treasury, name="add_treasury"),
    path('edit_treasury/<int:id>/', views.edit_treasury, name="edit_treasury"),
    path('delete_treasury/<int:id>/', views.delete_treasury, name="delete_treasury"),
    path('export/<int:id>/<str:date_from>/<str:date_to>/', views.export_treasury, name="export_treasury"),
    path('missions/<int:id>/', views.missions_index, name="missions_index"),
    path('details/<int:id>/', views.mission_details, name="mission_details"),
    path('add_mission/<int:id>/', views.add_mission, name="add_mission"),
    path('edit_mission/<int:id>/', views.edit_mission, name="edit_mission"),
    path('delete_mission/<int:id>/', views.delete_mission, name="delete_mission"),
    path('add_item/<int:id>/', views.add_mitem, name="add_mitem"),
    path('edit_item/<int:id>/', views.edit_mitem, name="edit_mitem"),
    path('delete_item/<int:id>/', views.delete_mitem, name="delete_mitem"),
    path('missions/fetch1/', views.fetch1, name="fetch1"),
    path('filter/<int:id>/', views.filter_invoices, name='filter_invoices'),
    path('pmissions/', views.pmissions_index, name='pmissions_index'),
    path('update_pmission_mmission/', views.update_pmission_mmission, name='update_pmission_mmission'),
    path('add_new_mission/', views.add_new_mission, name="add_new_mission"),
    path('get-location-suggestions/', views.get_location_suggestions, name='get_location_suggestions'),
    path('fetch-pmissions/', views.fetch_pmissions, name='fetch_pmissions'),
    path('mark-as-read/<int:mission_id>/', views.mark_as_read, name='mark_as_read'),
]






