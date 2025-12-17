"""
payments URLconf
"""
from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    path('upload/<int:entry_group_pk>/', views.payment_upload, name='upload'),
    path('status/<int:entry_group_pk>/', views.payment_status, name='status'),
    # 領収書ダウンロード
    path('receipt/<int:entry_group_pk>/download/', views.receipt_download, name='receipt_download'),
    path('admin/', views.payment_list, name='admin_list'),
    path('admin/<int:pk>/review/', views.payment_review, name='admin_review'),
    # 強制承認（トラブルデスク用）
    path('admin/force-approve/', views.force_approve_search, name='force_approve_search'),
    path('admin/force-approve/<int:competition_pk>/', views.force_approve_search, name='force_approve_search_competition'),
    path('admin/force-approve/entry-group/<int:entry_group_pk>/', views.force_approve, name='force_approve'),
    # 駐車場関連
    path('parking/<int:competition_pk>/', views.parking_request_view, name='parking_request'),
    path('parking/permit/<int:parking_request_pk>/download/', views.parking_permit_download, name='parking_permit_download'),
    # 駐車場管理（管理者用）
    path('admin/parking/<int:competition_pk>/import/', views.parking_csv_import, name='parking_csv_import'),
    path('admin/parking/template/', views.parking_csv_template, name='parking_csv_template'),
    path('admin/parking/<int:competition_pk>/all-permits/', views.all_permits_download, name='all_permits_download'),
]
