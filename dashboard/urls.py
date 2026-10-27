from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
   path('admin/', views.admin_dashboard, name='admin_dashboard'),
path('pm/', views.pm_dashboard, name='pm_dashboard'),
path('user/', views.user_dashboard, name='user_dashboard'),
]