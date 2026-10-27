from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('ask/', views.chatbot_ask, name='ask'),
      path('history/', views.chatbot_history, name='history'),
]