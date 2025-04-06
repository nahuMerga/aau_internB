import random
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from internships.models import ThirdYearStudentList  # Adjust if needed
from .models import OTPVerification



class SendOTPView(APIView):
    def post(self, request):
        university_id = request.data.get("university_id")
        if not university_id:
            return Response({"error": "university_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        # 🔍 Find student by university_id
        student = ThirdYearStudentList.objects.filter(university_id=university_id).first()
        if not student:
            return Response({"error": "Student not found in third-year database."}, status=status.HTTP_404_NOT_FOUND)

        # ✅ Generate random 6-digit OTP
        otp_code = str(random.randint(100000, 999999))

        # ✅ Save or update OTP entry in DB first
        otp_entry, created = OTPVerification.objects.update_or_create(
            university_id=university_id,
            defaults={
                "otp_code": otp_code,
                "created_at": timezone.now(),
                "attempt_count": 0,
                "locked_until": None,
                "otp_verified": False  # Make sure the OTP is marked as not verified
            }
        )

        # 📧 Send email via Gmail SMTP
        try:
            send_mail(
                subject="Your AAU Internship OTP Code",
                message=f"Hello {student.full_name},\n\nYour OTP code is: {otp_code}\nIt is valid for 10 minutes.\n\nAAU Internship Team",
                from_email="aau57.sis@gmail.com",  # Use the same Gmail address
                recipient_list=[student.institutional_email],  # Student's institutional email
                fail_silently=False,
            )
        except Exception as e:
            return Response({"error": f"Failed to send email: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "OTP has been sent to your institutional email."}, status=status.HTTP_200_OK)
