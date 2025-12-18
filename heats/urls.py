"""
heats URLconf
"""
from django.urls import path

from . import views

app_name = 'heats'

urlpatterns = [
    path('competition/<int:competition_pk>/', views.heat_management, name='management'),
    path('race/<int:race_pk>/', views.heat_list, name='list'),
    path('race/<int:race_pk>/generate/', views.generate_heats, name='generate'),
    path('<int:pk>/', views.heat_detail, name='detail'),
    path('<int:pk>/finalize/', views.finalize_heat, name='finalize'),
    path('move/', views.move_assignment, name='move'),
    path('competition/<int:competition_pk>/checkin/', views.checkin_search, name='checkin_search'),
    path('competition/<int:competition_pk>/checkin/dashboard/', views.checkin_dashboard, name='checkin_dashboard'),
    path('competition/<int:competition_pk>/checkin/status/', views.checkin_status_api, name='checkin_status_api'),
    path('competition/<int:competition_pk>/checkin/stats/', views.checkin_stats_partial, name='checkin_stats_partial'),
    path('assignment/<int:assignment_pk>/checkin/', views.checkin, name='checkin'),
    path('assignment/<int:assignment_pk>/dns/', views.mark_dns, name='dns'),
    # 一括処理
    path('competition/<int:competition_pk>/generate-all/', views.generate_all_heats, name='generate_all'),
    path('competition/<int:competition_pk>/assign-bibs/', views.assign_bib_numbers, name='assign_bibs'),
]
