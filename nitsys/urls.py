"""
URL configuration for nitsys project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from competitions.views import admin_checkin_select, admin_competition_select, admin_report_select

from .views import admin_guide_view, index_view

urlpatterns = [
    path('admin/guide/', admin_guide_view, name='admin_guide'),
    path('admin/', admin.site.urls),
    path('', index_view, name='index'),
    path('home/', index_view, name='home'),  # エラーページ用
    path('accounts/', include('accounts.urls')),
    path('competitions/', include('competitions.urls')),
    path('entries/', include('entries.urls')),
    path('payments/', include('payments.urls')),
    path('heats/', include('heats.urls')),
    path('reports/', include('reports.urls')),
    path('news/', include('news.urls')),
    path('api/', include('entries.api_urls')),
    
    # 管理者用大会選択ページ
    path('admin-panel/heats/', admin_competition_select, name='admin_competition_select'),
    path('admin-panel/reports/', admin_report_select, name='admin_report_select'),
    path('admin-panel/checkin/', admin_checkin_select, name='admin_checkin_select'),
]

# カスタムエラーハンドラー
handler400 = 'nitsys.error_handlers.handler400'
handler403 = 'nitsys.error_handlers.handler403'
handler404 = 'nitsys.error_handlers.handler404'
handler500 = 'nitsys.error_handlers.handler500'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
