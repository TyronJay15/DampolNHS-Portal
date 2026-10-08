"""Django settings for the Dampol NHS Grade Portal API.

Every secret and every production address comes from the environment (Railway variables in production,
backend/.env locally). With DEBUG off, the settings refuse to start when a production safeguard is missing.
"""
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


def _flag(name, default='false'):
    return os.environ.get(name, default).strip().lower() in ('true', '1', 'yes')


SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-only')
# Off unless the environment turns it on, so a server with a missing variable never runs in debug mode.
DEBUG = _flag('DEBUG')
TESTING = 'test' in sys.argv
RECAPTCHA_SECRET_KEY = '' if TESTING else os.environ.get('RECAPTCHA_SECRET_KEY', '').strip()
GEMINI_API_KEY = '' if TESTING else os.environ.get('GEMINI_API_KEY', '').strip()

ALLOWED_HOSTS = _csv_env('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver')
# Railway calls the health check from this host name, so it must be allowed or every deploy reads as unhealthy.
RAILWAY_HEALTHCHECK_HOST = 'healthcheck.railway.app'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
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
    'apps.guidance',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'config.middleware.ApiSecurityHeadersMiddleware',
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
# The Django admin console. Set a hard-to-guess path in production; "off" removes it entirely.
DJANGO_ADMIN_PATH = os.environ.get('DJANGO_ADMIN_PATH', 'admin/').strip().strip('/')

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

# apps.accounts.passwords adds the role rules on top (students 10 characters, staff 12, a letter and a number).
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 10},
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
MEDIA_ROOT = Path(os.environ.get('MEDIA_ROOT', BASE_DIR / 'media'))
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5173').rstrip('/')

# ---- Mail (Brevo). Secrets come from the environment, never from the Vite frontend. ----
# MAIL_TRANSPORT: "smtp" (Brevo SMTP relay) or "brevo_api" (Brevo HTTPS API, for hosts that block SMTP).
MAIL_TRANSPORT = os.environ.get('MAIL_TRANSPORT', 'smtp').strip().lower()
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '').strip()
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', '').strip()
EMAIL_FROM_NAME = os.environ.get('EMAIL_FROM_NAME', 'Dampol 1st NHS').strip()
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp-relay.brevo.com').strip()
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '').strip()
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '').strip()
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = 20
# Dev only: print activation and password codes in the terminal. Refused below when DEBUG is off.
MAIL_PRINT_CODES = _flag('MAIL_PRINT_CODES', 'true' if DEBUG else 'false')
# Registration emails wait in an outbox. "inline" sends right after saving (local use and tests).
# "background" leaves them to `manage.py send_outbox`, run by the host's always-on task or cron job.
MAIL_DELIVERY = os.environ.get('MAIL_DELIVERY', 'inline').strip().lower()
MAIL_DAILY_LIMIT = int(os.environ.get('MAIL_DAILY_LIMIT', '300'))  # Brevo free plan
MAIL_CODE_RESERVE = int(os.environ.get('MAIL_CODE_RESERVE', '50'))  # kept for activation and password codes
MAIL_KEEP_DAYS = int(os.environ.get('MAIL_KEEP_DAYS', '30'))
if MAIL_DELIVERY not in ('inline', 'background'):
    raise ImproperlyConfigured('MAIL_DELIVERY must be "inline" or "background".')
if MAIL_TRANSPORT not in ('smtp', 'brevo_api'):
    raise ImproperlyConfigured('MAIL_TRANSPORT must be "smtp" or "brevo_api".')
if TESTING:
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    MAIL_TRANSPORT = 'smtp'
    MAIL_PRINT_CODES = False
    MAIL_DELIVERY = 'inline'
    if not DEFAULT_FROM_EMAIL:
        DEFAULT_FROM_EMAIL = 'noreply@dampol1nhs.edu.ph'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    if MAIL_TRANSPORT == 'smtp' and not (EMAIL_HOST_USER and EMAIL_HOST_PASSWORD):
        raise ImproperlyConfigured('EMAIL_HOST_USER and EMAIL_HOST_PASSWORD (the Brevo SMTP login) are required.')
    if MAIL_TRANSPORT == 'brevo_api' and not BREVO_API_KEY:
        raise ImproperlyConfigured('BREVO_API_KEY is required when MAIL_TRANSPORT is "brevo_api".')
    if not DEFAULT_FROM_EMAIL:
        raise ImproperlyConfigured('DEFAULT_FROM_EMAIL is missing. Use a sender verified in Brevo.')

# ---- Sign-in sessions (apps.accounts.sessions). ----
# The access token lives only in the page's memory; the refresh token lives in an HttpOnly cookie that JavaScript
# cannot read, scoped to the sign-in endpoints. Values are the approved defaults of the security plan.
AUTH_ACCESS_MINUTES = int(os.environ.get('AUTH_ACCESS_MINUTES', '15'))
AUTH_IDLE_MINUTES = int(os.environ.get('AUTH_IDLE_MINUTES', '30'))
AUTH_SESSION_HOURS = int(os.environ.get('AUTH_SESSION_HOURS', '12'))
AUTH_REFRESH_GRACE_SECONDS = int(os.environ.get('AUTH_REFRESH_GRACE_SECONDS', '10'))
AUTH_REFRESH_COOKIE = 'dampol_refresh'
AUTH_REFRESH_COOKIE_PATH = '/api/auth/'
# "Lax" when the frontend and the API share a site (same domain or subdomains of one domain, the recommended set-up);
# "None" only when they are truly cross-site, and then only over HTTPS. See README, "Sign-in cookies".
AUTH_COOKIE_SAMESITE = os.environ.get('AUTH_COOKIE_SAMESITE', 'Lax').strip().capitalize()
if AUTH_COOKIE_SAMESITE not in ('Strict', 'Lax', 'None'):
    raise ImproperlyConfigured('AUTH_COOKIE_SAMESITE must be Strict, Lax or None.')
AUTH_COOKIE_SECURE = not DEBUG and not TESTING
if AUTH_COOKIE_SAMESITE == 'None' and not AUTH_COOKIE_SECURE and not TESTING:
    raise ImproperlyConfigured('AUTH_COOKIE_SAMESITE=None needs HTTPS: it is refused while DEBUG is on.')

# ---- Retention (apps.accounts.management.commands.daily_maintenance). ----
SESSION_KEEP_DAYS = int(os.environ.get('SESSION_KEEP_DAYS', '30'))
CHAT_QUESTION_KEEP_DAYS = int(os.environ.get('CHAT_QUESTION_KEEP_DAYS', '90'))
# Interest answers and saved recommendations for graduates, after the school year they last belonged to ended.
GUIDANCE_KEEP_DAYS = int(os.environ.get('GUIDANCE_KEEP_DAYS', '365'))

# ---- Cross-origin access. Only the listed frontend origins may call the API, and only they may send the
# sign-in cookie. The CSRF token (apps.accounts.csrf) protects the three endpoints that use that cookie. ----
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

# ---- Browser security headers and cookies. ----
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
# The frontend receives the CSRF token from /api/auth/csrf/ in the response body, so the cookie stays unreadable.
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = AUTH_COOKIE_SAMESITE

if not DEBUG and not TESTING:
    # Railway ends HTTPS at its proxy and passes X-Forwarded-Proto.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = _flag('SECURE_SSL_REDIRECT', 'true')
    # Platform probes may call plain HTTP inside the network. /api/health/ stays the deploy check.
    SECURE_REDIRECT_EXEMPT = [r'^api/health/$', r'^api/health/ready/$']
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # HSTS starts short; raise SECURE_HSTS_SECONDS to 31536000 once HTTPS on the final domain is confirmed.
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '3600'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = _flag('SECURE_HSTS_INCLUDE_SUBDOMAINS')
    SECURE_HSTS_PRELOAD = _flag('SECURE_HSTS_PRELOAD')
    if RAILWAY_HEALTHCHECK_HOST not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(RAILWAY_HEALTHCHECK_HOST)
    if not os.environ.get('NUM_PROXIES', '').strip().isdigit():
        raise ImproperlyConfigured(
            'NUM_PROXIES is required when DEBUG is false (1 on Railway), so rate limits see the real visitor address.'
        )
    if not CORS_ALLOWED_ORIGINS or any(origin == '*' or not origin.startswith('https://') for origin in CORS_ALLOWED_ORIGINS):
        raise ImproperlyConfigured('CORS_ALLOWED_ORIGINS must list only the https:// frontend address(es) when DEBUG is false.')
    if SECRET_KEY in ('django-insecure-dev-only', 'dev-only-change-me-use-a-long-random-string-32b') or len(SECRET_KEY) < 50:
        raise ImproperlyConfigured('SECRET_KEY must be a unique random value of at least 50 characters when DEBUG is false.')
    if not ALLOWED_HOSTS or set(ALLOWED_HOSTS) <= {'localhost', '127.0.0.1', 'testserver'}:
        raise ImproperlyConfigured('ALLOWED_HOSTS must include the public Django hostname when DEBUG is false.')
    if not FRONTEND_URL.startswith('https://') or 'localhost' in FRONTEND_URL:
        raise ImproperlyConfigured('FRONTEND_URL must be the https:// address of the frontend when DEBUG is false.')
    if not RECAPTCHA_SECRET_KEY:
        raise ImproperlyConfigured('RECAPTCHA_SECRET_KEY is required when DEBUG is false, so sign-in and registration are protected.')
    if MAIL_PRINT_CODES:
        raise ImproperlyConfigured('MAIL_PRINT_CODES must be off when DEBUG is false: codes must never reach the server logs.')

# ---- Logging. Everything goes to the console, which Railway keeps. 'apps.security' carries sign-in failures,
# locks and token replays; lines name accounts by id only (see apps.accounts.security_events). ----
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'plain': {'format': '{asctime} {levelname} {name}: {message}', 'style': '{'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'plain'}},
    'loggers': {
        'apps': {'handlers': ['console'], 'level': os.environ.get('APP_LOG_LEVEL', 'INFO'), 'propagate': False},
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}
if TESTING:
    LOGGING['loggers']['apps']['level'] = 'CRITICAL'
    LOGGING['loggers']['django']['level'] = 'ERROR'

# ---- API ----
# Request limits per endpoint group (see apps.accounts.throttles). An empty value means no limit, which the
# test suite uses; individual tests set their own limits. NUM_PROXIES tells DRF how many proxies sit in front
# (1 on Railway), so limits apply per visitor rather than per proxy.
API_THROTTLE_RATES = {} if TESTING else {
    'login': os.environ.get('THROTTLE_LOGIN', '30/min'),
    'login_account': os.environ.get('THROTTLE_LOGIN_ACCOUNT', '20/hour'),
    'refresh': os.environ.get('THROTTLE_REFRESH', '60/min'),
    'reports': os.environ.get('THROTTLE_REPORTS', '30/min'),
    'register': os.environ.get('THROTTLE_REGISTER', '60/hour'),
    'codes': os.environ.get('THROTTLE_CODES', '30/hour'),
    'chatbot': os.environ.get('THROTTLE_CHATBOT', '30/min'),
    'retrain': os.environ.get('THROTTLE_RETRAIN', '20/hour'),
    'email_resend': os.environ.get('THROTTLE_EMAIL_RESEND', '30/hour'),
    'guidance_answer': os.environ.get('THROTTLE_GUIDANCE_ANSWER', '300/hour'),
    'guidance_write': os.environ.get('THROTTLE_GUIDANCE_WRITE', '120/hour'),
    'catalog_import': os.environ.get('THROTTLE_CATALOG_IMPORT', '20/hour'),
}
_proxies = os.environ.get('NUM_PROXIES', '').strip()

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.accounts.authentication.PortalJWTAuthentication',
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
    'NUM_PROXIES': int(_proxies) if _proxies else None,
    # JSON only in production; the clickable browsable API is a development convenience.
    'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.JSONRenderer',)
    + (('rest_framework.renderers.BrowsableAPIRenderer',) if DEBUG else ()),
}

# College recommendation: share of a college program's skill areas that must be backed by
# the student's real grades for a match to count as strongly supported. Below it a match is
# shown as limited evidence. A design parameter, not a measured value; change it here or in .env.
MIN_RECOMMENDATION_EVIDENCE_COVERAGE = float(os.environ.get('MIN_RECOMMENDATION_EVIDENCE_COVERAGE', '0.6'))
# College catalog CSV import limits.
CATALOG_IMPORT_MAX_BYTES = 1024 * 1024
CATALOG_IMPORT_MAX_ROWS = 500
# A demo database for the defence. Only then may seed_demo_forecast add synthetic history.
# Off unless set explicitly; never set it on the real school's server.
DEMO_MODE = _flag('DEMO_MODE')

# Only access tokens are JWTs; refresh tokens are random values held by apps.accounts.sessions.
# The token carries the user id and the session id, nothing personal.
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=AUTH_ACCESS_MINUTES),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'UPDATE_LAST_LOGIN': False,
}
