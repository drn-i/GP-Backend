from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from .authentication import verify_firebase_token
from .models import Role

User = get_user_model()

class UserSyncView(APIView):
    """
    POST /api/v1/users/sync
    This endpoint bridges Firebase and MySQL.
    """
    permission_classes = [AllowAny]
    authentication_classes = []  

    def post(self, request):
        # 1. THE DEBUG PRINTS (Moved inside the actual request handler)
        auth_header = request.headers.get('Authorization')
        print(f"--- DEBUG START ---")
        print(f"Header: {auth_header}")
        print(f"--- DEBUG END ---")
        
        try:
            decoded_token = verify_firebase_token(request)
            if not decoded_token:
                return Response({"error": "Invalid token payload"}, status=401)
        except Exception as e:
            # 2. CATCHING THE 401 REASON
            # This will print the exact reason your authentication.py rejected the token!
            print(f"TOKEN REJECTED REASON: {str(e)}") 
            return Response({"error": str(e)}, status=401)
            
        uid = decoded_token.get('uid')
        email = decoded_token.get('email', '')

        # Syncing Firebase UID with local MySQL record
        user, created = User.objects.get_or_create(
            username=uid, 
            defaults={'email': email, 'is_active': True}
        )

        # Assign default role to new users
        if created:
            patient_role, _ = Role.objects.get_or_create(role_name='Patient')
            user.role = patient_role
            user.save()

        return Response({
            "status": "success",
            "local_id": user.id,
            "role": user.role.role_name if user.role else None,
            "created": created
        }, status=status.HTTP_200_OK)