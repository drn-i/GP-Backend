import os
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model

# This dynamically loads your custom users.User model!
User = get_user_model()

class StaticAPIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = get_authorization_header(request).decode('utf-8')
        
        if not auth_header:
            return None 

        token = auth_header.replace("Bearer ", "").strip()
        expected_n8n_token = os.environ.get('N8N_MASTER_TOKEN', 'amer_local_test_key').strip()
        expected_eyad_token = os.environ.get('EYAD_TEST_TOKEN', 'eyad_local_test_key').strip()

        if "." not in token:
            if token != expected_n8n_token and token != expected_eyad_token:
                raise AuthenticationFailed(
                    f"DEBUG MATCH FAILED! "
                    f"Django Expected: '{expected_n8n_token}' (Length: {len(expected_n8n_token)}) | "
                    f"Amer Sent: '{token}' (Length: {len(token)})"
                )

        # 1. N8N Service Account (Amer)
        if token == expected_n8n_token:
            user, _ = User.objects.get_or_create(username="n8n_service_account")
            user.is_staff = True 
            return (user, "StaticToken")

        # 2. Eyad Test Account
        if token == expected_eyad_token:
            user, _ = User.objects.get_or_create(username="S10") 
            user.is_staff = False
            return (user, "StaticToken")

        return None