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


class StudentRegistrationView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        university_id = request.data.get("university_id")
        phone_number = request.data.get("phone_number")
        telegram_id = request.data.get("telegram_id")

        if not self.OTPVerified():
            return Response({"OTPVerified": False, "error": "OTP verification failed."}, status=status.HTTP_400_BAD_REQUEST)

        internship_period = InternshipPeriod.objects.order_by("-registration_end").first()
        if not internship_period:
            return Response({"error": "Internship registration period is not set."}, status=status.HTTP_400_BAD_REQUEST)

        today = timezone.now().date()


        registration_ongoing = today <= internship_period.registration_end

        third_year_student = ThirdYearStudentList.objects.filter(university_id=university_id).first()
        if not third_year_student:
            return Response({"error": "Student not found in third-year database."}, status=status.HTTP_404_NOT_FOUND)

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

        return Response({
            "message": "Student registered successfully.",
            "OTPVerified": True,
            "student": {
                "university_id": student.university_id,
                "institutional_email": student.institutional_email,
                "full_name": student.full_name,
                "phone_number": student.phone_number,
                "telegram_id": student.telegram_id,
                "status": student.status,
                "start_date": student.start_date or None,
                "end_date": student.end_date or None,
                "student_grade": student.grade if hasattr(student, "grade") else 0,
                "assigned_advisor": student.assigned_advisor.full_name if student.assigned_advisor else "Pending (Not assigned yet)",
            },
            "intern_student": {
                "student": student.full_name,
            }
        }, status=status.HTTP_201_CREATED)

    def OTPVerified(self):
        """Dummy OTP verification, always returns True (replace later with real logic)."""
        return True



class InternshipOfferLetterUploadView(generics.CreateAPIView):
    """Upload an internship offer letter (Student instance is passed)"""
    serializer_class = InternshipOfferLetterSerializer
    permission_classes = [AllowAny]  # ✅ No authentication required

    def perform_create(self, serializer):
        student = serializer.validated_data.get("student")  # Get Student object
        if not student:
            raise ValidationError({"error": "Student object is required."})

        serializer.save(student=student)


class InternshipReportUploadView(generics.CreateAPIView):
    """Submit an internship report every 15 days (Student instance is passed)"""
    serializer_class = InternshipReportSerializer
    permission_classes = [AllowAny]  # ✅ No authentication required

    def perform_create(self, serializer):
        student = serializer.validated_data.get("student")  # Get Student object
        if not student:
            raise ValidationError({"error": "Student object is required."})

        # ✅ Check last report submission
        last_report = InternshipReport.objects.filter(student=student).order_by('-submission_date').first()
        if last_report and (timezone.now().date() - last_report.submission_date).days < 15:
            raise ValidationError({"error": "You can only submit a report every 15 days."})

        serializer.save(student=student)



