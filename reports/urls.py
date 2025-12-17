"""
reports URLconf
"""
from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('competition/<int:competition_pk>/', views.report_index, name='index'),
    path('race/<int:race_pk>/startlist.csv', views.download_startlist_csv, name='startlist_csv'),
    path('competition/<int:competition_pk>/all.csv', views.download_all_data_csv, name='all_data_csv'),
    path('heat/<int:heat_pk>/rollcall.pdf', views.download_rollcall_pdf, name='rollcall_pdf'),
    path('race/<int:race_pk>/program.pdf', views.download_program_pdf, name='program_pdf'),
    path('competition/<int:competition_pk>/emergency.pdf', views.download_all_data_pdf, name='all_data_pdf'),
    # 結果記録用紙
    path('heat/<int:heat_pk>/result_sheet.pdf', views.download_result_sheet_pdf, name='result_sheet_pdf'),
    path('race/<int:race_pk>/result_sheets.pdf', views.download_all_result_sheets_pdf, name='all_result_sheets_pdf'),
]
