from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from students.models import Student, InternshipOfferLetter, InternshipReport
from .serializers import StudentSerializer, InternshipOfferLetterSerializer, InternshipReportSerializer
from internships.models import ThirdYearStudentList, InternStudentList, InternshipPeriod
from django.utils import timezone
from rest_framework import status
from advisors.models import Advisor
from rest_framework.exceptions import NotAuthenticated, NotFound
from rest_framework.permissions import AllowAny
from .models import Student
from django.core.exceptions import ValidationError
from telegram_bot.models import OTPVerification


class StudentRegistrationView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        university_id = request.data.get("university_id")
        phone_number = request.data.get("phone_number")
        telegram_id = request.data.get("telegram_id")
        otp_code = request.data.get("otp_code")

        # Check if OTP is verified
        if not self.OTPVerified(university_id, otp_code):
            return Response({"OTPVerified": False, "error": "OTP verification failed or locked."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the registration period is active
        internship_period = InternshipPeriod.objects.order_by("-registration_end").first()
        today = timezone.now().date()
        if not internship_period.is_registration_active():
            return Response({"error": "The registration period has ended."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if internship calendar dates are valid
        if not internship_period.is_valid_calendar():
            return Response({"error": "The internship calendar dates are invalid."}, status=status.HTTP_400_BAD_REQUEST)

        # Find the student by university ID
        third_year_student = ThirdYearStudentList.objects.filter(university_id=university_id).first()
        if not third_year_student:
            return Response({"error": "Student not found in third-year database."}, status=status.HTTP_404_NOT_FOUND)

        # Create or update the student record
        student, _ = Student.objects.update_or_create(
            university_id=third_year_student.university_id,
            defaults={
                "full_name": third_year_student.full_name,
                "institutional_email": third_year_student.institutional_email,
                "phone_number": phone_number,
                "telegram_id": telegram_id,
                "status": "Pending",
                "assigned_advisor": None  # Advisor assignment handled separately
            }
        )

        # Create InternStudentList entry (Only if OTP is verified)
        intern_student, _ = InternStudentList.objects.update_or_create(
            student=third_year_student,
            defaults={}
        )

        # Mark OTP as verified in the student record
        self.mark_otp_verified(university_id)

        # Return success response with engaging message
        return Response({
            "message": f"🎉 Congratulations {student.full_name}! You have successfully registered! 🎉\nNow you can start using the mini app. 🚀\n\nWelcome to the AAU Internship System! 🏆\n\n👉 [Start using the mini app](http://your-mini-app-link.com) 👈",
            "OTPVerified": True,
        }, status=status.HTTP_201_CREATED)


    def OTPVerified(self, university_id, otp_code):
        try:
            otp_entry = OTPVerification.objects.get(university_id=university_id)
        except OTPVerification.DoesNotExist:
            return False

        if otp_entry.is_locked():
            return False

        if otp_entry.is_expired():
            otp_entry.delete()
            return False

        if otp_entry.otp_code != otp_code:
            otp_entry.attempt_count += 1
            if otp_entry.attempt_count >= 4:
                otp_entry.locked_until = timezone.now() + timedelta(hours=1)
            otp_entry.save()
            return False

        otp_entry.delete()  # Valid and used
        return True

    def mark_otp_verified(self, student):
        """Marks the student's otp_verified field as True."""
        if student:
            student.otp_verified = True  # Mark OTP as verified in the student record
            student.save()




class InternshipOfferLetterUploadView(generics.CreateAPIView):
    serializer_class = InternshipOfferLetterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        student = serializer.validated_data.get("student")

        if not student:
            raise ValidationError({"error": "Student object is required."})

        if not student.assigned_advisor:
            raise ValidationError({"error": "Advisor not assigned yet."})

        existing_letter = InternshipOfferLetter.objects.filter(student=student).first()
        if existing_letter and existing_letter.advisor_approved:
            raise ValidationError({"error": "An approved offer letter already exists."})

        serializer.save(student=student)
        


class InternshipReportUploadView(generics.CreateAPIView):
    serializer_class = InternshipReportSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        student = serializer.validated_data.get("student")
        report_number = serializer.validated_data.get("report_number")

        if not student:
            raise ValidationError({"error": "Student object is required."})

        if not student.assigned_advisor:
            raise ValidationError({"error": "Advisor not assigned yet."})

        if InternshipReport.objects.filter(student=student, report_number=report_number, advisor_approved=True).exists():
            raise ValidationError({"error": f"Report {report_number} already approved. You can't upload it again."})

        approved_reports_count = InternshipReport.objects.filter(student=student, advisor_approved=True).count()
        if approved_reports_count >= 4:
            raise ValidationError({"error": "You have already submitted 4 approved reports."})

        last_report = InternshipReport.objects.filter(student=student).order_by('-submission_date').first()
        if last_report and (timezone.now().date() - last_report.submission_date.date()).days < 15:
            raise ValidationError({"error": "You can only submit a report every 15 days."})

        serializer.save(student=student)



