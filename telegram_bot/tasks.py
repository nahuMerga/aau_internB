from celery import shared_task
from django.core.mail import send_mail
from .models import OTPVerification
import random
from django.utils import timezone

@shared_task(bind=True, max_retries=3)
def send_otp_email_task(self, university_id, student_name, student_email, otp_code):
    try:
        send_mail(
            subject="Your AAU Internship OTP Code",
            message=f"Hello {student_name},\n\nYour OTP code is: {otp_code}\nIt is valid for 10 minutes.\n\nAAU Internship Team",
            from_email="aau57.sis@gmail.com",
            recipient_list=[student_email],
            fail_silently=False,
        )
        return f"OTP email sent to {student_email}"
    except Exception as e:
        # Retry after 30 seconds if email fails
        self.retry(countdown=30, exc=e)
