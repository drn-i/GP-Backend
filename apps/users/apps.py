import os
from django.apps import AppConfig
from django.conf import settings
import firebase_admin
from firebase_admin import credentials

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    label = 'users'

    def ready(self):
        # Initialize Firebase only when Django is fully ready
        if not firebase_admin._apps:
            cred_path = os.path.join(settings.BASE_DIR, 'serviceAccountKey.json')
            try:
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                else:
                    print("WARNING: serviceAccountKey.json not found. Firebase Auth will fail.")
            except Exception as e:
                print(f"ERROR: Failed to initialize Firebase: {e}")
