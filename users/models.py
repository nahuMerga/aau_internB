# from django.contrib.auth.models import AbstractUser
# from django.db import models

# class CustomUser(AbstractUser):
#     ROLE_CHOICES = [
#         ("student", "Student"),
#         ("advisor", "Advisor"),
#     ]
#     role = models.CharField(max_length=10, choices=ROLE_CHOICES)
#     phone_number = models.CharField(max_length=15, blank=True, null=True)
#     telegram_id = models.CharField(max_length=50, blank=True, null=True)

#     def __str__(self):
#         return f"{self.username} ({self.role})"
