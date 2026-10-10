from pathlib import Path
from datetime import timedelta
from decouple import config, Csv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-default-key')

DEBUG = config('DEBUG', default=False, cast=bool)
DEMO_MODE = config('DEMO_MODE', default=True, cast=bool)
MASTER_ADMIN_USERNAME = config('MASTER_ADMIN_USERNAME', default='master_admin')

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=Csv())


# Application definition

INSTALLED_APPS = [
    "django_daisy",
    "django.contrib.admin",
    "django.contrib.humanize",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "adminsortable2",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",

    # Local apps
    "products",
    "accounts",
    "consultations",
    "qr_hub",
]

# Admin notification email for new consultation requests
# ADMIN_NOTIFICATION_EMAIL = "admin@suryatejahandlooms.com"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",      
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "myproject.middleware.ReadOnlyAdminMiddleware",
]

ROOT_URLCONF = "myproject.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "myproject" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.debug",
                "myproject.context_processors.admin_dashboard_stats",
            ],
        },
    },
]

WSGI_APPLICATION = "myproject.wsgi.application"
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:5173")
ADMIN_LOGIN_URL = config("ADMIN_LOGIN_URL", default=f"{FRONTEND_URL}/admin/login")
# WhatsApp Business / Personal number (with country code, no + or spaces)
WHATSAPP_NUMBER = config("WHATSAPP_NUMBER", default="919999999999")

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


STORAGES = {
    "default": {
        "BACKEND": "products.supabase_storage.SupabaseStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "accounts.auth_backend.EmailOrUsernameModelBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Session Persistence Configuration
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 14 days
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")



# Media files (uploaded images)
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")


# -------------------------------------------------
# Email - Gmail SMTP
# -------------------------------------------------

# settings.py

DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.postgresql"),
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 600,
        "CONN_HEALTH_CHECKS": True,
    }
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default=config("EMAIL_HOST_USER", default="surya.teja.handlooms@gmail.com"))
ADMIN_NOTIFICATION_EMAIL = config("ADMIN_NOTIFICATION_EMAIL", default=config("EMAIL_HOST_USER", default="surya.teja.handlooms@gmail.com"))

# Django Daisy Admin
ADMIN_SITE_TITLE = config("ADMIN_SITE_TITLE", default="Silk & Loom Admin")
ADMIN_SITE_HEADER = config("ADMIN_SITE_HEADER", default="Silk & Loom Administration")
ADMIN_INDEX_TITLE = config("ADMIN_INDEX_TITLE", default="Welcome to Silk & Loom Dashboard")

DAISY_SETTINGS = {
    "SITE_TITLE": ADMIN_SITE_TITLE,
    "SITE_HEADER": ADMIN_SITE_HEADER,
    "INDEX_TITLE": ADMIN_INDEX_TITLE,
    "SHOW_THEME_SELECTOR": True,
    "DEFAULT_THEME": "light",
    "DEFAULT_THEME_DARK": "dark",
}

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": None,  # Frontend currently does client-side pagination
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "accounts.authenticate.CookieJWTAuthentication",
    ),
    "DEFAULT_THROTTLE_CLASSES": [
        "myproject.throttling.PublicRateThrottle",
        "myproject.throttling.UserActionRateThrottle",
    ],
    "EXCEPTION_HANDLER": "myproject.exceptions.custom_exception_handler",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# WebP Conversion Settings & Mobile Upload Optimization
WEBP_QUALITY = config("WEBP_QUALITY", default=82, cast=int)
MAX_IMAGE_DIMENSION = config("MAX_IMAGE_DIMENSION", default=2048, cast=int)

# File & Data upload limits for high-resolution mobile camera uploads (50 MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 52,428,800 bytes
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 52,428,800 bytes
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000  # Support large inline formsets



# Reverse Proxy & SSL Configuration (Crucial for Render & Vercel HTTPS)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# CSRF & Session Cookie Settings
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "None" if not DEBUG else "Lax"

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    "https://saree-store-backend.vercel.app",
    "https://saree-store-backend-ex17.onrender.com",
    "https://silk-and-loom.vercel.app",
    "https://silk-loom-connect.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CSRF_TRUSTED_ORIGINS = [
    "https://saree-store-backend.vercel.app",
    "https://saree-store-backend-ex17.onrender.com",
    "https://*.onrender.com",
    "https://*.vercel.app",
    "https://silk-and-loom.vercel.app",
    "https://silk-loom-connect.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CORS_PREFLIGHT_MAX_AGE = 86400



CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "surya-handlooms-cache",
    }
}
