"""
competitions URLconf
"""
from django.urls import path

from . import views

app_name = 'competitions'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('list/', views.competition_list, name='list'),
    path('<int:pk>/', views.competition_detail, name='detail'),
    path('history/', views.entry_history, name='history'),
]
