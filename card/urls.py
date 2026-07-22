from django.urls import path
from . import views



urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='cards_index'),

      # Customers
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/add/', views.CustomerCreateView.as_view(), name='customer_add'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_edit'),
    path('customers/<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),
    path('customers/<int:pk>/balance/', views.CustomerBalanceView.as_view(), name='cardholder_balance'),
    path('customers/<int:pk>/statement/export/', views.export_cardholder_statement, name='cardholder_statement_export'),

    # Showrooms
    path('showrooms/add/', views.ShowroomCreateView.as_view(), name='showroom_add'),

    # Cards
    path('cards/', views.CardListView.as_view(), name='card_list'),
    path('cards/<int:pk>/', views.CardDetailView.as_view(), name='card_detail'),
    path('cards/add/', views.CardCreateView.as_view(), name='card_add'),
    path('cards/<int:pk>/edit/', views.CardUpdateView.as_view(), name='card_edit'),
    path('cards/<int:pk>/delete/', views.CardDeleteView.as_view(), name='card_delete'),
    path('cards/<int:pk>/print/', views.print_card, name='card_print'),

    # Card Payments (whether the card price itself has been paid)
    path('payments/', views.CardPaymentListView.as_view(), name='card_payments'),
    path('payments/<int:pk>/toggle/', views.toggle_card_paid, name='toggle_card_paid'),

    # Categories & Services (combined page)
    path('categories-services/', views.CategoryServiceView.as_view(), name='category_service'),

    # Categories
    path('categories/add/', views.CategoryCreateView.as_view(), name='category_add'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),

    # Services
    path('services/add/', views.ServiceCreateView.as_view(), name='service_add'),
    path('services/<int:pk>/edit/', views.ServiceUpdateView.as_view(), name='service_edit'),
    path('services/<int:pk>/delete/', views.ServiceDeleteView.as_view(), name='service_delete'),

    path('scan/<uuid:card_uuid>/', views.CardScanView.as_view(), name='card_scan'),
    path('request/<uuid:card_uuid>/submit/', views.SubmitServiceRequestView.as_view(), name='submit_request'),
    path('request/<int:pk>/status/', views.RequestStatusView.as_view(), name='request_status'),

    # STAFF: Bonus quota
    path('card/<int:card_pk>/add-bonus/', views.AddBonusQuotaView.as_view(), name='add_bonus'),
path('card/<int:pk>/requests/', views.card_requests, name='card_requests'),
    # STAFF: Request management
    path('requests/', views.ServiceRequestListView.as_view(), name='request_list'),
    path('requests/<int:pk>/update/', views.UpdateRequestStatusView.as_view(), name='update_request_status'),
    path('ajax/services-by-category/', views.get_services_by_category, name='services_by_category'),
    path('public/validate-card/', views.public_validate_card, name='public_validate_card'),
    path('public/submit-request/<int:card_id>/', views.SubmitServiceRequestView.as_view(), name='public_submit_request'),
    path('public/request-status/', views.public_request_status, name='public_request_status'),
    path('portal/', views.PublicPortalView.as_view(), name='public_portal'),
    path('request/<int:request_id>/mission/', views.create_update_mission, name='create_update_mission'),
    path('card/<int:card_id>/add-quota/', views.add_service_quota, name='add_service_quota'),

     path('reports/cards/', views.CardReportView.as_view(), name='card_report'),
    path('reports/services/', views.ServiceReportView.as_view(), name='service_report'),
    path('reports/card-lookup/', views.CardLookupView.as_view(), name='card_lookup'),

    # Invoices (overage / metered usage billing)
    path('invoices/', views.ServiceInvoiceListView.as_view(), name='invoice_list'),
    path('invoices/export/', views.export_invoices_csv, name='export_invoices_csv'),
    path('invoices/<int:pk>/print/', views.invoice_print, name='invoice_print'),
    path('invoices/<int:pk>/mark-paid/', views.mark_invoice_paid, name='mark_invoice_paid'),

    path('notifications/check/', views.check_new_requests, name='check_new_requests'),
path('notifications/mark-seen/', views.mark_requests_seen, name='mark_requests_seen'),
    path('fcm/register/', views.register_fcm_token, name='register_fcm_token'),
    path('fcm/test/', views.send_test_notification, name='send_test_notification'),

]