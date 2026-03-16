from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import MedicalProfile
from .serializers import MedicalProfileSerializer

class MyProfileManageView(APIView):
    """
    GET /api/v1/profiles/me/  -> Fetch my profile (creates a blank one automatically if missing)
    PUT /api/v1/profiles/me/  -> Update my profile
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile, created = MedicalProfile.objects.get_or_create(user=request.user)
        
        serializer = MedicalProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        profile, created = MedicalProfile.objects.get_or_create(user=request.user)

        serializer = MedicalProfileSerializer(profile, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        print("--- SERIALIZER REJECTED THE DATA! ---")
        print("EXACT ERRORS:", serializer.errors) 
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UpdateFCMTokenView(APIView):
    """
    POST /api/v1/profiles/update-fcm-token/ -> Update the user's FCM token for push notifications
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        fcm_token = request.data.get('fcm_token')
        
        if not fcm_token:
            return Response(
                {"error": "FCM_TOKEN_REQUIRED: 'fcm_token' field is required in the request body."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            profile, _ = MedicalProfile.objects.get_or_create(user=request.user)
            profile.fcm_token = fcm_token
            profile.save()
            return Response({"status": "success", "message": "FCM token updated successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"An error occurred while updating the FCM token: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )