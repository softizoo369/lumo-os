"""
Django settings for Lumo OS project.
Optimized for Server-Side Rendering (HTMX) & Production-Ready SaaS.
"""
import os 
from pathlib import Path
import environ

# 1. PATH CONFIGURATION
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. ENVIRONMENT VARIABLES SETUP
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['*'])
)
# Read .env file if it exists
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# 3. SECURITY SETTINGS
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
# ALLOWED_HOSTS = env('ALLOWED_HOSTS')
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'mycompany.local']
# 4. APPLICATION DEFINITION
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize', # <-- এই লাইনটি যোগ করুন
]

THIRD_PARTY_APPS = [
    'rest_framework',  # Only for Client Storefront APIs in the future
]

# Our Custom Domains (Inside apps/ folder)
LUMO_OS_APPS = [
    'apps.identity',  
    'apps.saas_core',
    'apps.core_masterdata',
    'apps.lumo_sites',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LUMO_OS_APPS

# 5. CUSTOM USER MODEL (Mandatory for Identity App)
AUTH_USER_MODEL = 'identity.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', # Session must be first
    'django.middleware.common.CommonMiddleware',
    
    # 🟢 1. Lumo OS Tenant Routing (Must be before Auth)
    'apps.saas_core.middleware.TenantRoutingMiddleware',
    
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', # Auth must be after session
    'django.contrib.messages.middleware.MessageMiddleware',
    
    # 🔴 2. CUSTOM SAAS SECURITY MIDDLEWARE
    'apps.saas_core.middleware.TenantMiddleware', 
    'apps.saas_core.middleware.SaaSEnforcementMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

# 6. TEMPLATES (Configured for SSR & HTMX)
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
                'apps.saas_core.context_processors.global_saas_settings',
                'apps.saas_core.context_processors.global_notifications',
            ],
        },
    },
]

# 7. DATABASE CONFIGURATION (PostgreSQL)
DATABASES = {
    'default': env.db('DATABASE_URL', default='sqlite:///db.sqlite3')
}

# 8. CACHING (Redis for Sessions, Rate Limiting & Settings)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env('REDIS_URL', default='redis://127.0.0.1:6379/1'),
    }
}

# 9. PASSWORD VALIDATION & AUTHENTICATION
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 10. INTERNATIONALIZATION
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC' # Always store time in UTC, convert in UI
USE_I18N = True
USE_TZ = True

# 11. STATIC & MEDIA FILES
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')



MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 12. CELERY CONFIGURATION (Background Tasks)
CELERY_BROKER_URL = env('REDIS_URL', default='redis://127.0.0.1:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# Development Environment Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'lumo-os-cache',
    }
}

# ==========================================
# STRIPE PAYMENT GATEWAY SETTINGS
# ==========================================
# আপাতত আমরা Test Mode-এর ডামি-কি বসাচ্ছি। লাইভে যাওয়ার আগে আসল Key বসিয়ে দেবো।
STRIPE_PUBLIC_KEY = "pk_test_dummy_key_123"
STRIPE_SECRET_KEY = "sk_test_dummy_key_123"
STRIPE_WEBHOOK_SECRET = "whsec_dummy_secret_123"

CF_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")
CF_ZONE_ID = os.environ.get("CLOUDFLARE_ZONE_ID")   