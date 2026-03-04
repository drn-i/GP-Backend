from django.contrib import admin
from .models import MedicalProfile

@admin.register(MedicalProfile)
class MedicalProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'gender', 'dob', 'created_at')
    search_fields = ('user__email', 'user__username')
    list_filter = ('created_at', 'gender')
    
    fieldsets = (
        ('Base Profile', {
            'fields': ('user', 'height', 'weight', 'gender', 'dob')
        }),
        ('Step 1: Medical History', {
            'fields': ('chronic_diseases', 'previous_surgeries', 'major_injuries', 'disabilities_genetic_conditions')
        }),
        ('Step 2: Medications & Allergies', {
            'fields': ('ongoing_treatments', 'supplements', 'medication_allergies', 'current_medications')
        }),
        ('Step 3: Specific Allergy Details', {
            'fields': ('allergy_type', 'allergy_severity', 'allergy_symptoms', 'emergency_medication', 's3_additional_notes')
        }),
        ('Step 4: Family History', {
            'fields': ('family_chronic_diseases', 'family_genetic_disorders', 'family_members_health', 's4_additional_notes')
        }),
        ('Step 5: Lifestyle', {
            'fields': ('physical_activity_level', 'diet_type', 'average_sleep_hours', 'smoking_habits', 's5_additional_notes')
        }),
        ('Step 6: Current State', {
            'fields': ('current_symptoms', 'daily_energy_level', 'sleep_quality', 'physical_limitations', 's6_additional_notes')
        }),
        ('Step 7: Mental Health', {
            'fields': ('general_mood', 'stress_level', 'emotional_support', 'psychological_consultations', 's7_additional_notes')
        }),
        ('Step 8: Vaccinations', {
            'fields': ('vaccines_received', 'vaccine_date_administered', 'missed_vaccines', 'vaccine_side_effects', 's8_additional_notes')
        }),
        ('Step 9: Recent Checkups', {
            'fields': ('last_general_checkup', 'last_blood_test', 'last_eye_examination', 'doctors_notes', 's9_additional_notes')
        }),
    )