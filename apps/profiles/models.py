from django.db import models
from django.conf import settings

class MedicalProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # --- BASE PROFILE ---
    height = models.FloatField(help_text="Height in cm", null=True, blank=True)
    weight = models.FloatField(help_text="Weight in kg", null=True, blank=True)
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    dob = models.DateField(verbose_name="Date of Birth", null=True, blank=True)
    fcm_token = models.CharField(max_length=255, blank=True, null=True, help_text="Firebase Device Token for Push Notifications")

    # --- REGISTRATION STEP 1 ---
    chronic_diseases = models.TextField(help_text="Step 1: Chronic Diseases", blank=True, null=True)
    previous_surgeries = models.TextField(help_text="Step 1: Previous Surgeries", blank=True, null=True)
    major_injuries = models.TextField(help_text="Step 1: Major Injuries", blank=True, null=True)
    disabilities_genetic_conditions = models.TextField(help_text="Step 1: Disabilities or Genetic Conditions", blank=True, null=True)

    # --- REGISTRATION STEP 2 ---
    ongoing_treatments = models.TextField(help_text="Step 2: Ongoing Treatments", blank=True, null=True)
    supplements = models.TextField(help_text="Step 2: Supplements", blank=True, null=True)
    medication_allergies = models.TextField(help_text="Step 2: Medication Allergies", blank=True, null=True)
    current_medications = models.TextField(help_text="Step 2: Current Medications", blank=True, null=True)

    # --- REGISTRATION STEP 3 ---
    allergy_type = models.CharField(max_length=255, help_text="Step 3: Allergy Type", blank=True, null=True)
    allergy_severity = models.CharField(max_length=100, help_text="Step 3: Severity", blank=True, null=True)
    allergy_symptoms = models.TextField(help_text="Step 3: Common Symptoms", blank=True, null=True)
    emergency_medication = models.TextField(help_text="Step 3: Emergency Medication", blank=True, null=True)
    s3_additional_notes = models.TextField(help_text="Step 3: Additional Notes", blank=True, null=True)

    # --- REGISTRATION STEP 4 ---
    family_chronic_diseases = models.TextField(help_text="Step 4: Chronic Diseases in Family", blank=True, null=True)
    family_genetic_disorders = models.TextField(help_text="Step 4: Genetic Disorders", blank=True, null=True)
    family_members_health = models.TextField(help_text="Step 4: Family Members' Health", blank=True, null=True)
    s4_additional_notes = models.TextField(help_text="Step 4: Additional Notes", blank=True, null=True)

    # --- REGISTRATION STEP 5 ---
    physical_activity_level = models.CharField(max_length=100, help_text="Step 5: Physical Activity Level", blank=True, null=True)
    diet_type = models.CharField(max_length=100, help_text="Step 5: Diet Type", blank=True, null=True)
    average_sleep_hours = models.FloatField(help_text="Step 5: Average Sleep Hours", blank=True, null=True)
    smoking_habits = models.CharField(max_length=100, help_text="Step 5: Smoking Habits", blank=True, null=True)
    s5_additional_notes = models.TextField(help_text="Step 5: Additional Notes", blank=True, null=True)

    # --- REGISTRATION STEP 6 ---
    current_symptoms = models.TextField(help_text="Step 6: Current Symptoms", blank=True, null=True)
    daily_energy_level = models.CharField(max_length=100, help_text="Step 6: Daily Energy Level", blank=True, null=True)
    sleep_quality = models.CharField(max_length=100, help_text="Step 6: Sleep Quality", blank=True, null=True)
    physical_limitations = models.TextField(help_text="Step 6: Physical Limitations", blank=True, null=True)
    s6_additional_notes = models.TextField(help_text="Step 6: Additional Notes", blank=True, null=True)

    # --- REGISTRATION STEP 7 ---
    general_mood = models.CharField(max_length=100, help_text="Step 7: General Mood", blank=True, null=True)
    stress_level = models.CharField(max_length=100, help_text="Step 7: Stress Level", blank=True, null=True)
    emotional_support = models.CharField(max_length=255, help_text="Step 7: Emotional Support Availability", blank=True, null=True)
    psychological_consultations = models.TextField(help_text="Step 7: Previous Psychological Consultations", blank=True, null=True)
    s7_additional_notes = models.TextField(help_text="Step 7: Additional Notes", blank=True, null=True)

    # --- REGISTRATION STEP 8 ---
    vaccines_received = models.TextField(help_text="Step 8: Vaccines Received", blank=True, null=True)
    vaccine_date_administered = models.TextField(help_text="Step 8: Date Administered (List)", blank=True, null=True)
    missed_vaccines = models.TextField(help_text="Step 8: Missed Vaccines", blank=True, null=True)
    vaccine_side_effects = models.TextField(help_text="Step 8: Notable Side Effects", blank=True, null=True)
    s8_additional_notes = models.TextField(help_text="Step 8: Additional Notes", blank=True, null=True)

    # --- REGISTRATION STEP 9 ---
    last_general_checkup = models.DateField(help_text="Step 9: Last General Checkup", blank=True, null=True)
    last_blood_test = models.DateField(help_text="Step 9: Last Blood Test", blank=True, null=True)
    last_eye_examination = models.DateField(help_text="Step 9: Last Eye Examination", blank=True, null=True)
    doctors_notes = models.TextField(help_text="Step 9: Doctor's Notes or Recommendations", blank=True, null=True)
    s9_additional_notes = models.TextField(help_text="Step 9: Additional Notes", blank=True, null=True)
    
    def __str__(self):
        return f"Profile: {self.user.username}"