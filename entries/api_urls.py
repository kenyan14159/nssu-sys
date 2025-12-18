"""
entries API URLconf
"""
from django.urls import path

from . import api_views

urlpatterns = [
    path('athletes/', api_views.athlete_list, name='api_athlete_list'),
    path('entries/', api_views.entry_list, name='api_entry_list'),
    path('assignments/<int:pk>/', api_views.assignment_detail, name='api_assignment_detail'),
]
