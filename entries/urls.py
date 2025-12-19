"""
entries URLconf
"""
from django.urls import path

from . import views

app_name = 'entries'

urlpatterns = [
    path('competition/<int:competition_pk>/race/<int:race_pk>/create/', views.entry_create, name='create'),
    path('competition/<int:competition_pk>/cart/', views.entry_cart, name='cart'),
    path('competition/<int:competition_pk>/confirm/', views.entry_confirm, name='confirm'),
    path('competition/<int:competition_pk>/save-draft/', views.entry_save_draft, name='save_draft'),
    path('competition/<int:competition_pk>/excel/template/', views.excel_template_download, name='excel_template'),
    path('competition/<int:competition_pk>/excel/upload/', views.excel_upload, name='excel_upload'),
    path('competition/<int:competition_pk>/confirmation-pdf/', views.entry_confirmation_pdf, name='confirmation_pdf'),
    path('<int:pk>/', views.entry_detail, name='detail'),
    path('<int:pk>/delete/', views.entry_delete, name='delete'),
]
