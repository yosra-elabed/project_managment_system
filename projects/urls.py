from django.urls import path
from . import views

app_name = 'projects'
urlpatterns = [
    path('create/', views.project_create_view, name='project_create'),
    path('list/', views.project_list, name='project_list'),
    path('detail/<int:pk>/', views.project_detail, name='project_detail'),
       path('edit/<int:pk>/', views.project_edit_view, name='project_edit'),
       path('delegations/', views.delegation_list, name='delegation_list'),
        path('<int:project_pk>/delegate/', views.delegation_create, name='delegation_create'),
    path('delegation/<int:pk>/end/', views.delegation_end, name='delegation_end'),
    path('delegate/new/', views.delegation_create_generic, name='delegation_create_generic'),

]