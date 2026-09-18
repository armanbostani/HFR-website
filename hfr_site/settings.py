from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-only-change-this-key')
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Production hardening. Everything here switches on when DEBUG is off,
# so the live server only needs the environment variables set.
if not DEBUG:
    from django.core.exceptions import ImproperlyConfigured
    if SECRET_KEY == 'dev-only-change-this-key':
        raise ImproperlyConfigured('Set DJANGO_SECRET_KEY before running with DEBUG off.')
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30

_csrf_origins = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '')
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = _csrf_origins.split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'recruitment',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hfr_site.urls'

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
                'core.context_processors.site',
            ],
        },
    },
]

WSGI_APPLICATION = 'hfr_site.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'Europe/London'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Applicant CVs live outside MEDIA_ROOT so they are never web-served
# directly; team leads download them through a permission-checked view.
PRIVATE_MEDIA_ROOT = BASE_DIR / 'private_media'

# Email. Printed to the console in development; real SMTP settings come
# from the environment on the live server (needed for password resets).
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('DJANGO_EMAIL_HOST', '')
    EMAIL_PORT = int(os.environ.get('DJANGO_EMAIL_PORT', '587'))
    EMAIL_HOST_USER = os.environ.get('DJANGO_EMAIL_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('DJANGO_EMAIL_PASSWORD', '')
    EMAIL_USE_TLS = os.environ.get('DJANGO_EMAIL_USE_TLS', '1') == '1'
# The society's contact address, shown wherever the public site says "email
# us" (store orders, sponsorship, donations). One variable changes it everywhere.
CONTACT_EMAIL = os.environ.get('HFR_CONTACT_EMAIL', 'hfr@glasgow.ac.uk')
DEFAULT_FROM_EMAIL = os.environ.get('DJANGO_DEFAULT_FROM_EMAIL', f'HFR <{CONTACT_EMAIL}>')

# Members' forum (Discourse). While FORUM_URL is empty the site shows nothing
# about the forum. Setting DISCOURSE_CONNECT_SECRET as well switches on single
# sign-on, so members log in to the forum with their website account
# (see DEPLOYMENT.md).
FORUM_URL = os.environ.get('HFR_FORUM_URL', '').strip().rstrip('/')
DISCOURSE_CONNECT_SECRET = os.environ.get('HFR_DISCOURSE_CONNECT_SECRET', '')

AUTHENTICATION_BACKENDS = ['recruitment.backends.FlexibleLoginBackend']

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'account_router'
LOGOUT_REDIRECT_URL = 'home'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
