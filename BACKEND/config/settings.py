"""
Django settings for config project.
"""

from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Seguridad / Debug ---
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "smart-condominium-1.onrender.com",
]

# --- Apps ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "corsheaders",
    "django_filters",
    "rest_framework",
    "rest_framework.authtoken",
    "storages",   # habilita S3 si lo usas en prod

    "smartcondominio.apps.SmartCondominioConfig",
]

# --- Middleware ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise debe ir lo más arriba posible, después de SecurityMiddleware
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

# --- Templates ---
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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Base de datos ---
# Usa DATABASE_URL si está definido, si no, cae a SQLite.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        ssl_require=os.getenv("DATABASE_URL", "").startswith(("postgres://", "postgresql://")),
    )
}

# --- Password validators ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- i18n ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Static ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# WhiteNoise: compresión + manifest para cache busting
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

LOGIN_URL = "signin"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- CORS / CSRF ---
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN")

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://smart-condominium-2.onrender.com",
]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "https://smart-condominium-1.onrender.com",
    "https://smart-condominium-2.onrender.com",
]

# --- DRF ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

# --- Proxy SSL (Render/Heroku) ---
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Media ---
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Almacenamiento en S3 (opcional; activa con STORAGE_BACKEND=s3)
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")  # "local" | "s3"
if STORAGE_BACKEND == "s3":
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-1")
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True

# --- Integraciones (ej. Stripe) ---
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# --- Base URL pública del sitio (para armar links absolutos en pagos/mock) ---
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8000")


#ia
load_dotenv()
PLATE_RECOG_TOKEN = os.getenv("PLATE_RECOG_TOKEN", "")
PLATE_REGIONS = os.getenv("PLATE_REGIONS", "bo")
OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.60"))
VISITOR_TIME_TOLERANCE_MIN = int(os.getenv("VISITOR_TIME_TOLERANCE_MIN", "10"))

OPEN_ON_ALLOW = os.getenv("OPEN_ON_ALLOW", "false").lower() == "true"

FACE_THRESHOLD = float(os.environ.get("FACE_THRESHOLD", "0.40"))