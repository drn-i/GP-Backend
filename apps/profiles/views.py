from rest_framework import generics, permissions
from .models import MedicalProfile
from .serializers import MedicalProfileSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_profile(request):
    # request.user is set by your Firebase Middleware based on the token
    user = request.user 
    profile = user.profile # Note: changed to user.profile based on your related_name in models.py
    
    return Response({
        "email": user.email,
        "height": profile.height,
        "weight": profile.weight,
        "dob": profile.dob,
        "gender": profile.gender
    }, status=200)

class ProfileCreateView(generics.CreateAPIView):
    """
    POST /api/v1/profiles
    Auto-assigns the authenticated user.
    """
    queryset = MedicalProfile.objects.all()
    serializer_class = MedicalProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)