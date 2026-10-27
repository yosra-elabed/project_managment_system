from django.urls import path
from . import views

app_name = 'statuses'

urlpatterns = [
    path('project/<int:pk>/', views.project_status_view, name='project_status'),
    path('project/<int:pk>/report/pdf/', views.project_status_report_pdf, name='project_status_report_pdf'),
    path('history/<int:history_pk>/pdf/', views.department_status_history_pdf, name='history_entry_pdf'),
    path('report/<int:pk>/release/', views.release_status_report, name='release_report'),
]