from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from firebase_admin import auth
from django.contrib.auth import get_user_model

# 🛑 CRITICAL FIX: Always get the custom User model dynamically
User = get_user_model()

def verify_firebase_token(request):
    """Parse and verify a Firebase ID token from the Authorization header."""
    # Support both Django's request.META and DRF's request.headers
    auth_header = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION')

    if not auth_header:
        raise AuthenticationFailed("No Authorization header provided.")

    parts = auth_header.split()
    if parts[0].lower() != 'bearer':
        raise AuthenticationFailed("Authorization header must start with Bearer.")
    if len(parts) == 1:
        raise AuthenticationFailed("Token missing.")
    if len(parts) > 2:
        raise AuthenticationFailed("Authorization header must be 'Bearer <token>'.")

    token = parts[1]

    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise AuthenticationFailed(f"Invalid Firebase token: {str(e)}")


class FirebaseAuthentication(BaseAuthentication):
    """
    Django REST Framework Authentication Class.
    Used automatically by 'IsAuthenticated' permissions on protected views.
    """
    def authenticate(self, request):
        # 1. Use your helper function! If the header is missing, 
        # this will now RAISE an error instead of returning None.
        decoded_token = verify_firebase_token(request)
        uid = decoded_token.get('uid')

        # 2. Statefulness Check: Does this user exist in our MySQL DB?
        try:
            # We strictly use .get() here instead of .get_or_create(). 
            # If they hit /profiles/ without calling /sync/ first, we block them.
            user = User.objects.get(username=uid)
            return (user, decoded_token)

        except User.DoesNotExist:
            raise AuthenticationFailed("User valid in Firebase but not synced to local DB. Call /api/v1/users/sync/ first.")

    def authenticate_header(self, request):
        """
        This forces DRF to return a 401 Unauthorized instead of a 403 Forbidden 
        if the token is completely missing.
        """
        return 'Bearer'