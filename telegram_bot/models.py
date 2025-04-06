from django.db import models
from django.utils import timezone
from datetime import timedelta

class OTPVerification(models.Model):
    university_id = models.CharField(max_length=50)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    attempt_count = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    otp_verified = models.BooleanField(default=False) 

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def is_locked(self):
        return self.locked_until and timezone.now() < self.locked_until

    def __str__(self):
        return f"{self.university_id} - {self.otp_code}"
