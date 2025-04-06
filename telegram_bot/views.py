import random
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from internships.models import ThirdYearStudentList
from .models import OTPVerification

class SendOTPView(APIView):
    def post(self, request):
        university_id = request.data.get("university_id")
        student = ThirdYearStudentList.objects.filter(university_id=university_id).first()

        if not student:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        otp = str(random.randint(100000, 999999))
        OTPVerification.objects.update_or_create(
            university_id=university_id,
            defaults={
                "otp_code": otp,
                "created_at": timezone.now(),
                "attempt_count": 0,
                "locked_until": None
            }
        )

        send_mail(
            subject="Your OTP Code",
            message=f"Your OTP code is {otp}. It is valid for 10 minutes.",
            from_email="no-reply@yourdomain.com",
            recipient_list=[student.institutional_email],
            fail_silently=False,
        )

        return Response({"message": "OTP sent successfully."}, status=status.HTTP_200_OK)
