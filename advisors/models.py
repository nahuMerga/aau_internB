from django.db import models
from django.contrib.auth.models import User
from django.core.validators import EmailValidator

class Advisor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)  
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    # university_email = models.EmailField(
    #     unique=True,
    #     validators=[EmailValidator(message="Must be a valid university email")]
    # )
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    number_of_expected_reports = models.PositiveIntegerField(default=4)
    report_submission_interval_days = models.PositiveIntegerField(default=15)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
