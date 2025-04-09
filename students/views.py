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
import os
import requests


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
        
        
# def upload_to_supabase(file, path_in_bucket):
#     url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{path_in_bucket}"

#     headers = {
#         "apikey": SUPABASE_API_KEY,
#         "Authorization": f"Bearer {SUPABASE_API_KEY}",
#         "Content-Type": "application/octet-stream",
#         "x-upsert": "true"
#     }

#     response = requests.post(url, headers=headers, data=file.read())

#     if response.status_code in [200, 201]:
#         return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{path_in_bucket}"
#     else:
#         raise Exception(f"Upload failed: {response.status_code} - {response.text}")


def upload_to_supabase(file, path_in_bucket):
    SUPABASE_URL = "https://cavdgitwbubdtqdctvlz.supabase.co"
    SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNhdmRnaXR3YnViZHRxZGN0dmx6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQxOTUyMTQsImV4cCI6MjA1OTc3MTIxNH0.Xs8TmxZbub6C4WK8qwCiZ0pPfbXbPLDIyandKuyUtgY"
    SUPABASE_BUCKET = "student-document"

    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{path_in_bucket}"

    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/octet-stream",
        "x-upsert": "true"
    }

    response = requests.post(url, headers=headers, data=file.read())

    if response.status_code in [200, 201]:
        return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{path_in_bucket}"
    else:
        raise Exception(f"Upload failed: {response.status_code} - {response.text}")




class InternshipOfferLetterUploadView(generics.CreateAPIView):
    serializer_class = InternshipOfferLetterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        telegram_id = serializer.validated_data.get('telegram_id')
        company = serializer.validated_data.get('company')
        uploaded_file = serializer.validated_data.get('document')

        student = Student.objects.filter(telegram_id=telegram_id).first()

        if not student:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

        if not student.otp_verified:
            return Response({"error": "OTP verification required"}, status=status.HTTP_403_FORBIDDEN)

        if not student.assigned_advisor:
            return Response({"error": "Advisor not assigned yet"}, status=status.HTTP_400_BAD_REQUEST)

        if InternshipOfferLetter.objects.filter(student=student, advisor_approved='Approved').exists():
            return Response({"error": "Approved offer letter already exists"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Upload to Supabase
            file_path = f"offer_letters/{telegram_id}/{uploaded_file}"
            file_url = upload_to_supabase(uploaded_file, file_path)
            
            # Save to database - using your existing model structure
            offer_letter = InternshipOfferLetter.objects.create(
                student=student,
                company=company,
                document=uploaded_file  # Store the file in your model's FileField
            )
            
            # If you want to store the Supabase URL, you could add it to a field if available
            # offer_letter.supabase_url = file_url
            # offer_letter.save()

            return Response({
                "message": "✅ Offer letter submitted successfully!",
                "details": f"Company: {company}",
                "status": "Pending advisor approval",
                "supabase_url": file_url  # Returning URL in response
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InternshipReportUploadView(generics.CreateAPIView):
    serializer_class = InternshipReportSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        telegram_id = serializer.validated_data.get('telegram_id')
        report_number = serializer.validated_data.get('report_number')
        uploaded_file = serializer.validated_data.get('document')

        student = Student.objects.filter(telegram_id=telegram_id).first()

        if not student:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check if offer letter exists and is approved
        offer_letter = InternshipOfferLetter.objects.filter(student=student).first()
        if not offer_letter or offer_letter.advisor_approved != 'Approved':
            return Response({"error": "Approved offer letter required"}, status=status.HTTP_400_BAD_REQUEST)

        # Check report sequence
        existing_reports = InternshipReport.objects.filter(student=student)
        if existing_reports.filter(report_number=report_number).exists():
            return Response({"error": f"Report {report_number} already submitted"}, status=status.HTTP_400_BAD_REQUEST)

        expected_report = existing_reports.count() + 1
        if report_number != expected_report:
            return Response({
                "error": f"Expected report #{expected_report} next",
                "current_progress": f"{existing_reports.count()}/4 reports submitted"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Upload to Supabase
            file_path = f"reports/{telegram_id}/{uploaded_file}"
            file_url = upload_to_supabase(uploaded_file, file_path)
            
            # Save to database
            report = InternshipReport.objects.create(
                student=student,
                report_number=report_number,
                document=uploaded_file  # Using your model's FileField
            )

            progress = f"{report_number}/4 reports submitted"
            remaining = 4 - report_number

            return Response({
                "message": f"📘 Report {report_number} submitted successfully!",
                "progress": progress,
                "remaining_reports": remaining,
                "company": offer_letter.company,
                "supabase_url": file_url
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        

class OfferLetterStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        telegram_id = request.query_params.get('telegram_id')
        if not telegram_id:
            return Response({"error": "telegram_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        student = Student.objects.filter(telegram_id=telegram_id).first()
        if not student:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

        offer = InternshipOfferLetter.objects.filter(student=student).first()
        advisor_name = f"{student.assigned_advisor.first_name} {student.assigned_advisor.last_name}" if student.assigned_advisor else None

        # Prepare the response
        response_data = {
            "student_name": student.full_name,
            "advisor_name": advisor_name,
            "offer_letter": {
                "uploaded": bool(offer),
                "approved": offer.advisor_approved if offer else False,
                "company": offer.company if offer else None,
                "document": request.build_absolute_uri(offer.document.url) if offer and offer.document else None
            }
        }

        return Response(response_data)



class ReportStatusView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        telegram_id = request.GET.get("telegram_id")
        if not telegram_id:
            return Response({"error": "telegram_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        student = Student.objects.filter(telegram_id=telegram_id).first()
        if not student:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

        reports = []
        existing_reports = {r.report_number: r for r in InternshipReport.objects.filter(student=student)}

        for i in range(1, 5):
            report = existing_reports.get(i)
            reports.append({
                "report_number": i,
                "uploaded": bool(report),
                "document": request.build_absolute_uri(report.document.url) if report and report.document else None
            })

        return Response({
            "student_name": student.full_name,
            "advisor_name": f"{student.assigned_advisor.first_name} {student.assigned_advisor.last_name}" if student.assigned_advisor else None,
            "reports": reports
        })


