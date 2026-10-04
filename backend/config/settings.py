"""Django settings for the Dampol NHS Grade Portal API."""
import os
import sys
from datetime import timedelta
from pathlib import Path

import pymysql
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def _csv_env(name, default=''):
    return [
        part.strip().rstrip('/')
        for part in os.environ.get(name, default).split(',')
        if part.strip()
    ]


SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-only')
DEBUG = os.environ.get('DEBUG', 'true').lower() in ('true', '1', 'yes')
RECAPTCHA_SECRET_KEY = '' if 'test' in sys.argv else os.environ.get('RECAPTCHA_SECRET_KEY', '')
GEMINI_API_KEY = '' if 'test' in sys.argv else os.environ.get('GEMINI_API_KEY', '').strip()

ALLOWED_HOSTS = _csv_env('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'apps.accounts',
    'apps.school',
    'apps.people',
    'apps.grading',
    'apps.cms',
    'apps.audit',
    'apps.chatbot',
    'apps.notifications',
    'apps.access',
    'apps.ml',
]

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
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

pymysql.install_as_MySQLdb()
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'dampol_portal'),
        'USER': os.environ.get('DB_USER', 'root'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5173').rstrip('/')
# Brevo SMTP. Secrets come from the environment, never from the Vite frontend.
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', '').strip()
EMAIL_FROM_NAME = os.environ.get('EMAIL_FROM_NAME', 'Dampol 1st NHS').strip()
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp-relay.brevo.com').strip()
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '').strip()
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '').strip()
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = 20
MAIL_PRINT_CODES = os.environ.get('MAIL_PRINT_CODES', 'true' if DEBUG else 'false').lower() in ('true', '1', 'yes')
# Registration emails wait in an outbox. "inline" sends right after saving (local use and tests).
# "background" leaves them to `manage.py send_outbox`, run by the host's always-on task or cron job.
MAIL_DELIVERY = os.environ.get('MAIL_DELIVERY', 'inline').strip().lower()
MAIL_DAILY_LIMIT = int(os.environ.get('MAIL_DAILY_LIMIT', '300'))  # Brevo free plan
MAIL_CODE_RESERVE = int(os.environ.get('MAIL_CODE_RESERVE', '50'))  # kept for activation and password codes
MAIL_KEEP_DAYS = int(os.environ.get('MAIL_KEEP_DAYS', '30'))
if MAIL_DELIVERY not in ('inline', 'background'):
    raise ImproperlyConfigured('MAIL_DELIVERY must be "inline" or "background".')
if 'test' in sys.argv:
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    MAIL_PRINT_CODES = False
    MAIL_DELIVERY = 'inline'
    if not DEFAULT_FROM_EMAIL:
        DEFAULT_FROM_EMAIL = 'noreply@dampol1nhs.edu.ph'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    if not EMAIL_HOST_PASSWORD:
        raise ImproperlyConfigured(
            'EMAIL_HOST_PASSWORD is missing. Mail cannot start without the Brevo SMTP key.'
        )
    if not EMAIL_HOST_USER:
        raise ImproperlyConfigured('EMAIL_HOST_USER is missing. Set the Brevo SMTP login.')
    if not DEFAULT_FROM_EMAIL:
        raise ImproperlyConfigured(
            'DEFAULT_FROM_EMAIL is missing. Use a sender verified in Brevo.'
        )

_LOCAL_CORS = (
    'http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,'
    'http://127.0.0.1:5174,http://localhost:5175,http://127.0.0.1:5175'
)
CORS_ALLOWED_ORIGINS = _csv_env('CORS_ALLOWED_ORIGINS', _LOCAL_CORS if DEBUG else '')
if FRONTEND_URL and FRONTEND_URL not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS.append(FRONTEND_URL)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = list(CORS_ALLOWED_ORIGINS)
for origin in _csv_env('CSRF_TRUSTED_ORIGINS'):
    if origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)
if DEBUG:
    CORS_ALLOWED_ORIGIN_REGEXES = [r'^http://(localhost|127\.0\.0\.1):\d+$']
else:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    if SECRET_KEY in ('django-insecure-dev-only', 'dev-only-change-me-use-a-long-random-string-32b'):
        raise ImproperlyConfigured('SECRET_KEY must be a unique value when DEBUG is false.')
    if not ALLOWED_HOSTS or set(ALLOWED_HOSTS) <= {'localhost', '127.0.0.1', 'testserver'}:
        raise ImproperlyConfigured(
            'ALLOWED_HOSTS must include the public Django hostname when DEBUG is false.'
        )
    if not FRONTEND_URL.startswith('https://') or 'localhost' in FRONTEND_URL:
        raise ImproperlyConfigured(
            'FRONTEND_URL must be https://dampol1nhsportal.web.app when DEBUG is false.'
        )

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'EXCEPTION_HANDLER': 'config.exceptions.api_exception_handler',
}

# College recommendation: share of a college program's skill areas that must be backed by
# the student's real grades for a match to count as strongly supported. Below it a match is
# shown as limited evidence. A design parameter, not a measured value; change it here or in .env.
MIN_RECOMMENDATION_EVIDENCE_COVERAGE = float(os.environ.get('MIN_RECOMMENDATION_EVIDENCE_COVERAGE', '0.6'))

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=int(os.environ.get('JWT_ACCESS_MINUTES', '60'))
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=int(os.environ.get('JWT_REFRESH_DAYS', '7'))
    ),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
