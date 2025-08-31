import random
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from internships.models import ThirdYearStudentList  
from .models import OTPVerification
from .tasks import send_otp_email_task


class SendOTPView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        university_id = request.data.get("university_id")
        if not university_id:
            return Response({"error": "university_id is required."}, status=status.HTTP_400_BAD_REQUEST)


        student = ThirdYearStudentList.objects.filter(university_id=university_id).first()
        if not student:
            return Response({"error": "Student not found in third-year database."}, status=status.HTTP_404_NOT_FOUND)


        otp_code = str(random.randint(100000, 999999))


        otp_entry, created = OTPVerification.objects.update_or_create(
            university_id=university_id,
            defaults={
                "otp_code": otp_code,
                "created_at": timezone.now(),
                "attempt_count": 0,
                "locked_until": None,
                "otp_verified": False  
            }
        )

        send_otp_email_task.delay(
            university_id, 
            student.full_name, 
            student.institutional_email, 
            otp_code
        )

        return Response({"message": "OTP has been sent to your institutional email."}, status=status.HTTP_200_OK)
