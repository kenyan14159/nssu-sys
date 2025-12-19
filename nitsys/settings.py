"""
Django settings for nitsys project.
日本体育大学長距離競技会 エントリー・運営管理システム
"""

from pathlib import Path

import sentry_sdk
from decouple import Csv, config
from sentry_sdk.integrations.django import DjangoIntegration

# =============================================================================
# Sentry Error Monitoring (本番環境でのエラー通知)
# =============================================================================
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        # パフォーマンス監視（本番で10%のトランザクションをサンプリング）
        traces_sample_rate=0.1,
        # セッションリプレイ（オプション）
        profiles_sample_rate=0.1,
        # 送信するPII情報
        send_default_pii=False,
        # 環境名
        environment=config('SENTRY_ENVIRONMENT', default='production'),
    )


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Application definition
INSTALLED_APPS = [
    # Jazzmin must be before django.contrib.admin
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Third party apps
    'rest_framework',
    'corsheaders',
    'auditlog',
    # Local apps
    'accounts.apps.AccountsConfig',
    'competitions',
    'entries',
    'payments',
    'heats',
    'reports',
    'news',
]

# =============================================================================
# Jazzmin Admin Settings (モダンな管理画面テーマ)
# =============================================================================
JAZZMIN_SETTINGS = {
    # サイト設定
    "site_title": "日体大競技会",
    "site_header": "日体大競技会",
    "site_brand": "NIT-SYS",
    "site_logo": None,  # ロゴ画像は使用しない（文字のみ）
    "login_logo": "images/logo.svg",
    "login_logo_dark": "images/logo.svg",
    "site_logo_classes": "",
    "site_icon": "images/favicon.svg",
    "welcome_sign": "管理システムへようこそ",
    "copyright": "日本体育大学陸上競技部",
    
    # ユーザーアバター
    "user_avatar": None,
    
    # トップメニューリンク
    "topmenu_links": [
        {"name": "ホーム", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "ガイド", "url": "/admin/guide/", "new_window": False},
        {"name": "サイト", "url": "/", "new_window": True},
    ],
    
    # サイドメニュー
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": ["heats"],
    "hide_models": [],
    
    # カスタムリンク（heatsのモデルをcompetitionsに追加）
    "custom_links": {
        "competitions": [
            {
                "name": "組",
                "url": "admin:heats_heat_changelist",
                "icon": "fas fa-stopwatch",
                "permissions": ["heats.view_heat"]
            },
            {
                "name": "組編成",
                "url": "admin:heats_heatassignment_changelist",
                "icon": "fas fa-list-ol",
                "permissions": ["heats.view_heatassignment"]
            },
        ],
    },
    
    # アプリの日本語名
    "custom_app_names": {
        "accounts": "ユーザー管理",
        "competitions": "大会・種目",
        "entries": "エントリー",
        "payments": "入金管理",
        "heats": "番組編成",
        "reports": "レポート",
        "news": "お知らせ",
        "auth": "権限設定",
        "auditlog": "操作履歴",
    },
    
    # アプリの順序
    "order_with_respect_to": [
        "accounts",
        "competitions", 
        "entries",
        "payments",
        "heats",
        "reports",
        "news",
        "auth",
        "auditlog",
    ],
    
    # アイコン (Font Awesome 5)
    "icons": {
        "accounts.User": "fas fa-user",
        "accounts.Organization": "fas fa-building",
        "accounts.Athlete": "fas fa-running",
        "competitions.Competition": "fas fa-trophy",
        "competitions.Race": "fas fa-flag",
        "entries.Entry": "fas fa-clipboard-list",
        "entries.EntryGroup": "fas fa-layer-group",
        "payments.Payment": "fas fa-credit-card",
        "payments.BankAccount": "fas fa-university",
        "payments.ParkingRequest": "fas fa-car",
        "heats.Heat": "fas fa-stopwatch",
        "heats.HeatAssignment": "fas fa-list-ol",
        "reports.ReportLog": "fas fa-file-alt",
        "news.News": "fas fa-bullhorn",
        "auth.Group": "fas fa-users-cog",
        "auditlog.LogEntry": "fas fa-history",
    },
    
    # デフォルトアイコン
    "default_icon_parents": "fas fa-folder",
    "default_icon_children": "fas fa-circle fa-xs",
    
    # 関連モーダル
    "related_modal_active": True,
    
    # カスタムCSS/JS
    "custom_css": "css/admin_custom.css",
    "custom_js": "js/admin_custom.js",
    "use_google_fonts_cdn": True,
    "show_ui_builder": False,
    
    # チェンジビューのボタン
    "changeform_format": "single",
    "changeform_format_overrides": {},
    
    # 言語
    "language_chooser": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-primary",
    "accent": "accent-primary",
    "navbar": "navbar-dark navbar-primary",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    },
    "actions_sticky_top": True,
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Audit Log Middleware
    'auditlog.middleware.AuditlogMiddleware',
    # セキュリティミドルウェア
    'accounts.middleware.SessionIdleTimeoutMiddleware',
    'accounts.middleware.SecurityLoggingMiddleware',
]

ROOT_URLCONF = 'nitsys.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'nitsys.wsgi.application'

# Database
# PostgreSQL for production (transaction support)
if config('DATABASE_URL', default=None):
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(default=config('DATABASE_URL'))
    }
elif config('USE_SQLITE', default=False, cast=bool):
    # ローカル開発用（SQLite）
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='nitsys'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default='postgres'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'OPTIONS': {
                'connect_timeout': 10,
            },
            'ATOMIC_REQUESTS': True,  # トランザクション処理を確実に
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Internationalization
LANGUAGE_CODE = 'ja'
TIME_ZONE = 'Asia/Tokyo'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# 本番環境ではWhiteNoiseを使用、開発/テスト環境では標準のStorageを使用
if DEBUG:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
else:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (Uploaded files)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login settings
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'competitions:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

# CORS settings
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:8000', cast=Csv())

# CSRF Trusted Origins（開発環境とproduction両方に対応）
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:8000,http://127.0.0.1:8000',
    cast=Csv()
)

# 開発環境でのCSRF設定
if DEBUG:
    # VS Code Simple Browserなど埋め込みブラウザでの問題を回避
    CSRF_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SAMESITE = 'Lax'

# Security settings for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB

# Session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400  # 24 hours (絶対タイムアウト)
SESSION_IDLE_TIMEOUT = 1800  # 30 minutes (アイドルタイムアウト)
SESSION_SAVE_EVERY_REQUEST = True  # 毎リクエストでセッション更新

# Email settings
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@nitsys.jp')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'security': {
            'format': '[SECURITY] {levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'security_console': {
            'class': 'logging.StreamHandler',
            'formatter': 'security',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': config('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        # セキュリティログ（ログイン、認可エラー等）
        'security': {
            'handlers': ['security_console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
