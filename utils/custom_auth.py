import os
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import User

class StaticAPIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = get_authorization_header(request).decode('utf-8')
        
        if not auth_header:
            return None 

        token = auth_header.replace("Bearer ", "").strip()
        expected_n8n_token = os.environ.get('N8N_MASTER_TOKEN', 'amer_local_test_key').strip()
        expected_eyad_token = os.environ.get('EYAD_TEST_TOKEN', 'eyad_local_test_key').strip()

        # --- THE DEBUG TRAP ---
        # Firebase JWTs always contain dots (.). If there are no dots, 
        # we know it's Amer or Eyad trying to use a static token!
        if "." not in token:
            if token != expected_n8n_token and token != expected_eyad_token:
                # This explicitly crashes the request and sends this exact message back to n8n
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