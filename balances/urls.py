from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="balances_index"),
    path('logout/', views.logout_user, name="logout_user"),
    path('add_pmission/<int:customer_id>/', views.add_pmission, name='add_pmission'),
    path('edit_pmission/<int:id>/<int:customer_id>/', views.edit_pmission, name='edit_pmission'),
    path('delete_pmission/<int:id>/<int:customer_id>/', views.delete_pmission, name='delete_pmission'),
    path('import_excel/<int:id>/', views.import_excel, name='import_excel'),
    path('job_index/<str:username>/<str:password>/', views.job_index, name='job_index'),
    path('add_cost_center/<int:customer_id>/', views.add_cost_center, name='add_cost_center'),
    path('delete_cost_center/<int:id>/<int:customer_id>/', views.delete_cost_center, name='delete_cost_center'),
    path('top_customers/<str:date_from>/<str:date_to>/', views.top_customers_pdf, name='top_customers_pdf'),
    path('top_drivers/<str:date_from>/<str:date_to>/', views.top_drivers_pdf, name='top_drivers_pdf'),
    path('ranking_data/', views.ranking_data, name='ranking_data'),
]






