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
from datetime import timedelta


class StudentRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        university_id = request.data.get("university_id")
        phone_number = request.data.get("phone_number")
        telegram_id = request.data.get("telegram_id")
        otp_code = request.data.get("otp_code")

        if not university_id or not phone_number or not telegram_id or not otp_code:
            return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

        if not self.OTPVerified(university_id, otp_code):
            return Response({
                "OTPVerified": False,
                "error": "OTP verification failed or locked."
            }, status=status.HTTP_400_BAD_REQUEST)

        internship_period = InternshipPeriod.objects.order_by("-registration_end").first()
        today = timezone.now().date()

        if not internship_period or not internship_period.is_valid_calendar():
            return Response({
                "error": "The internship calendar dates are invalid."
            }, status=status.HTTP_400_BAD_REQUEST)

        third_year_student = ThirdYearStudentList.objects.filter(university_id=university_id).first()
        if not third_year_student:
            return Response({
                "error": "Student not found in third-year database."
            }, status=status.HTTP_404_NOT_FOUND)

        student, _ = Student.objects.update_or_create(
            university_id=third_year_student.university_id,
            defaults={
                "full_name": third_year_student.full_name,
                "institutional_email": third_year_student.institutional_email,
                "phone_number": phone_number,
                "telegram_id": telegram_id,
                "status": "Pending",
                "assigned_advisor": None
            }
        )

        InternStudentList.objects.update_or_create(
            student=third_year_student,
            defaults={}
        )

        self.mark_otp_verified(university_id)

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

        otp_entry.delete()
        return True

    def mark_otp_verified(self, university_id):
        student = Student.objects.get(university_id=university_id)
        student.otp_verified = True
        student.save()


class InternshipOfferLetterUploadView(generics.CreateAPIView):
    serializer_class = InternshipOfferLetterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        telegram_id = serializer.validated_data.pop('telegram_id')
        student = Student.objects.filter(telegram_id=telegram_id).first()

        if not student:
            return Response({"error": "Student not found with provided telegram_id"}, status=status.HTTP_404_NOT_FOUND)

        if not student.otp_verified:
            return Response({"error": "OTP verification is required before uploading documents."}, status=status.HTTP_403_FORBIDDEN)

        if not student.assigned_advisor:
            return Response({"error": "Advisor not assigned yet"}, status=status.HTTP_400_BAD_REQUEST)

        if InternshipOfferLetter.objects.filter(student=student, advisor_approved=True).exists():
            return Response({"error": "Approved offer letter already exists"}, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(student=student)

        return Response({
            "message": "✅ Offer letter submitted successfully! 📄\nYou will be notified once it's approved ✅"
        }, status=status.HTTP_201_CREATED)


class InternshipReportUploadView(generics.CreateAPIView):
    serializer_class = InternshipReportSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        telegram_id = serializer.validated_data.pop('telegram_id')
        report_number = serializer.validated_data.get('report_number')

        student = Student.objects.filter(telegram_id=telegram_id).first()

        if not student:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

        if not student.otp_verified:
            return Response({"error": "OTP verification is required before uploading documents."}, status=status.HTTP_403_FORBIDDEN)

        if not student.assigned_advisor:
            return Response({"error": "Advisor not assigned yet"}, status=status.HTTP_400_BAD_REQUEST)

        if InternshipReport.objects.filter(student=student, report_number=report_number).exists():
            return Response({"error": f"Report {report_number} already submitted"}, status=status.HTTP_400_BAD_REQUEST)

        total_reports = InternshipReport.objects.filter(student=student).count()
        if total_reports >= 4:
            return Response({"error": "Maximum 4 reports allowed"}, status=status.HTTP_400_BAD_REQUEST)

        expected_next_report = total_reports + 1
        if report_number != expected_next_report:
            return Response({
                "error": f"You must submit Report {expected_next_report} next. Report {report_number} is out of order."
            }, status=status.HTTP_400_BAD_REQUEST)

        last_report = InternshipReport.objects.filter(student=student).order_by('-submission_date').first()
        if last_report and (timezone.now() - last_report.submission_date) < timedelta(minutes=1):
            return Response({"error": "1-minute cooldown between reports (testing only)"}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        serializer.save(student=student)

        total_reports += 1
        remaining = max(0, 4 - total_reports)

        return Response({
            "message": f"📘 Report {report_number} submitted successfully!\nKeep going! 💪 You have {remaining} report(s) to go!"
        }, status=status.HTTP_201_CREATED)
