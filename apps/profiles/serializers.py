from rest_framework import serializers
from .models import MedicalProfile

class MedicalProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalProfile
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']