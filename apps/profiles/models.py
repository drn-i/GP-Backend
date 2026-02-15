from django.db import models
from django.conf import settings

class MedicalProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    height = models.FloatField(help_text="Height in cm")
    weight = models.FloatField(help_text="Weight in kg")
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    dob = models.DateField(verbose_name="Date of Birth")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile: {self.user.email}"