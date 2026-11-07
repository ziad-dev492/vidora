import os
from pathlib import Path
from urllib.parse import urlparse, unquote

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-before-deployment")
DEBUG = os.getenv("DEBUG", "0").lower() in {"1", "true", "yes"}
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "ALLOWED_HOSTS",
        "*" if DEBUG else "localhost,127.0.0.1",
    ).split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    x.strip() for x in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if x.strip()
]
BRAND_NAME = os.getenv("VIDORA_BRAND_NAME", "Vidora").strip() or "Vidora"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "apps.accounts.apps.AccountsConfig",
    "apps.channels.apps.ChannelsConfig",
    "apps.videos.apps.VideosConfig",
    "apps.interactions.apps.InteractionsConfig",
    "apps.playlists.apps.PlaylistsConfig",
    "apps.discovery.apps.DiscoveryConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.analytics.apps.AnalyticsConfig",
    "apps.moderation.apps.ModerationConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "config.context_processors.site_settings",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


def database_config():
    if os.getenv("SQLITE_USE", "0").lower() in {"1", "true", "yes"}:
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
    raw = os.getenv("DATABASE_URL", "postgresql://vidora:vidora@localhost:5432/vidora")
    parsed = urlparse(raw)
    if parsed.scheme in {"postgres", "postgresql", "postgresql+psycopg"}:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed.path.lstrip("/")),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "localhost",
            "PORT": str(parsed.port or 5432),
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {"connect_timeout": 5},
        }
    raise ValueError(
        "DATABASE_URL must use PostgreSQL; set SQLITE_USE=1 only for tests/demo."
    )


DATABASES = {"default": database_config()}
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "ar"
LANGUAGES = [("ar", "العربية"), ("en", "English")]
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Riyadh")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
WHITENOISE_MANIFEST_STRICT = not DEBUG
if os.getenv("VIDEO_STORAGE", "local").lower() == "s3":
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": os.getenv("AWS_STORAGE_BUCKET_NAME"),
            "region_name": os.getenv("AWS_S3_REGION_NAME") or None,
            "access_key": os.getenv("AWS_ACCESS_KEY_ID") or None,
            "secret_key": os.getenv("AWS_SECRET_ACCESS_KEY") or None,
            "file_overwrite": False,
            "querystring_auth": True,
        },
    }
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Local HTTP development can override these in .env. Public HTTPS Preview/production must set
# SESSION_COOKIE_SECURE=1; cookie policy is independent of the internal proxy's HTTP transport.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = os.getenv(
    "SESSION_COOKIE_SECURE", "0" if DEBUG else "1"
).lower() in {"1", "true", "yes"}
SESSION_COOKIE_SAMESITE = "None" if SESSION_COOKIE_SECURE else "Lax"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "0" if DEBUG else "1").lower() in {
    "1",
    "true",
    "yes",
}
CSRF_COOKIE_SAMESITE = "None" if CSRF_COOKIE_SECURE else "Lax"
CSRF_COOKIE_HTTPONLY = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Vidora <no-reply@example.test>")
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "0").lower() in {"1", "true", "yes"}
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "0").lower() in {"1", "true", "yes"}
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "10"))
MAX_VIDEO_UPLOAD_MB = int(os.getenv("MAX_VIDEO_UPLOAD_MB", "2048"))
MAX_IMAGE_UPLOAD_MB = int(os.getenv("MAX_IMAGE_UPLOAD_MB", "8"))
ENABLE_HLS = os.getenv("ENABLE_HLS", "0").lower() in {"1", "true", "yes"}
FILE_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 16 * 1024 * 1024
FILE_UPLOAD_PERMISSIONS = 0o640

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHES = (
    {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "vidora-development",
        }
    }
    if DEBUG
    else {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "vidora",
            "TIMEOUT": 300,
        }
    }
)
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "0").lower() in {
    "1",
    "true",
    "yes",
}
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 60
CELERY_TASK_TIME_LIMIT = 60 * 60 + 60

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication"
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly"
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 24,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/hour",
        "user": "1200/hour",
        "upload": "20/hour",
    },
}

if not DEBUG:
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "1").lower() in {
        "1",
        "true",
        "yes",
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}
