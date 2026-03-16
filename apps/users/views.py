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
        auth_header = request.headers.get('Authorization')
        
        try:
            decoded_token = verify_firebase_token(request)
            if not decoded_token:
                return Response({"error": "Invalid token payload"}, status=401)
        except Exception as e:
            print(f"TOKEN REJECTED REASON: {str(e)}") 
            return Response({"error": str(e)}, status=401)
            
        uid = decoded_token.get('uid')
        # Fallback to request.data if Firebase token doesn't have the email
        email = decoded_token.get('email', request.data.get('email', ''))
        phone_number = decoded_token.get('phone_number', '')

        # THE FIX: Safely extract names from the JSON body
        display_name = request.data.get('display_name', 'Unknown User')
        name_parts = display_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        try:
            # Syncing Firebase UID with a MySQL record using ALL required fields
            user, created = User.objects.get_or_create(
                username=uid, 
                defaults={
                    'email': email, 
                    'phone_number': phone_number, 
                    'is_active': True,
                    'first_name': first_name,
                    'last_name': last_name
                }
            )

            if created:
                # Give Firebase users an unusable password so the DB doesn't crash on the password_hash field
                user.set_unusable_password()
                
                # Assign default role
                patient_role, _ = Role.objects.get_or_create(role_name='Patient')
                user.role = patient_role
                user.save()

            return Response({
                "status": "success",
                "local_id": user.id,
                "role": user.role.role_name if user.role else None,
                "created": created
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            # If the database ever crashes again, it will now tell you EXACTLY why instead of a silent 500
            return Response({"error": f"Database Sync Failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)