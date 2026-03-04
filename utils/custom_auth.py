import os
from rest_framework.authentication import BaseAuthentication
from rest_framework import AuthenticationFailed
from django.contrib.auth.models import User

class StaticAPIKeyAuthentication(BaseAuthentication):
    """
    Allows n8n (Amer) and Swagger/Postman (Eyad) to bypass Firebase 
    using static, never-expiring API tokens.
    """
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        # Extract the token
        token = auth_header.replace("Bearer ", "").strip()
        expected_n8n_token = os.environ.get('N8N_MASTER_TOKEN', 'amer_local_test_key')
        
        # --- THE DEBUG TRAP ---
        # If the token doesn't match Firebase format (doesn't have dots), 
        # and it's not empty, force Django to print the mismatch!
        if "." not in token:
            raise AuthenticationFailed(f"DEBUG -> Django Expected: '{expected_n8n_token}' | Django Received: '{token}'")

        # 1. N8N Service Account (Amer)
        if token == expected_n8n_token:
            user, _ = User.objects.get_or_create(username="n8n_service_account")
            user.is_staff = True 
            return (user, "StaticToken")

        # 2. Eyad Test Account
        if token == os.environ.get('EYAD_TEST_TOKEN', 'eyad_local_test_key'):
            user, _ = User.objects.get_or_create(username="S10") 
            user.is_staff = False
            return (user, "StaticToken")

        return None