from rest_framework import serializers
from .models import MedicalProfile

class MedicalProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalProfile
        fields = ['id', 'height', 'weight', 'gender', 'dob']
        read_only_fields = ['id']