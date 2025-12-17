"""
accounts URLconf
"""
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('athletes/', views.athlete_list, name='athlete_list'),
    path('athletes/create/', views.athlete_create, name='athlete_create'),
    path('athletes/<int:pk>/edit/', views.athlete_edit, name='athlete_edit'),
    path('athletes/<int:pk>/delete/', views.athlete_delete, name='athlete_delete'),
    
    # 選手一括登録
    path('athletes/bulk/template/', views.athlete_bulk_template, name='athlete_bulk_template'),
    path('athletes/bulk/upload/', views.athlete_bulk_upload, name='athlete_bulk_upload'),
    path('athletes/bulk/register/', views.athlete_bulk_register, name='athlete_bulk_register'),
    
    # パスワードリセット
    path('password_reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/password_reset_email.html',
             subject_template_name='accounts/password_reset_subject.txt',
             success_url='/accounts/password_reset/done/'
         ), 
         name='password_reset'),
    path('password_reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             success_url='/accounts/reset/done/'
         ), 
         name='password_reset_confirm'),
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]
