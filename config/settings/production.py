import os
from .base import * 
import json
import firebase_admin
from firebase_admin import credentials

DEBUG = False

# 1. SECURITY: GET KEYS FROM DOKPLOY ENVIRONMENT
SECRET_KEY = os.environ.get('SECRET_KEY')

# Defines who can connect to your app
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'hypertrack.duckdns.org').split(',')

# 2. DATABASE: CONNECT TO YOUR DOKPLOY MYSQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_NAME", "gp_main_db"),
        "USER": os.environ.get("DB_USER", "gp_admin"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# 3. STATIC FILES
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# The modern way to declare storage backends in Django 5.1+
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
# 4. SECURITY & SSL (HTTPS)
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ⚠️ THE "MAGIC" FIX FOR DOKPLOY/TRAEFIK
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# 5. TRUSTED ORIGINS (REQUIRED FOR DJANGO 4.0+)
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://localhost').split(',')

# Allow FlutterFlow to communicate with the production API
CORS_ALLOW_ALL_ORIGINS = True

# Initialize Firebase Admin securely from Dokploy Environment Variables
firebase_creds_json = os.environ.get('FIREBASE_CREDS')

if firebase_creds_json:
    try:
        cred_dict = json.loads(firebase_creds_json)
        cred = credentials.Certificate(cred_dict)
        
        # Prevent Django from crashing by trying to initialize Firebase twice
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"CRITICAL: Failed to initialize Firebase: {e}")
else:
    print("WARNING: FIREBASE_CREDS environment variable is missing!")