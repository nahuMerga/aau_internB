from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from students.models import Student, InternshipOfferLetter, InternshipReport
from .serializers import StudentSerializer, InternshipOfferLetterSerializer, InternshipReportSerializer
from internships.models import ThirdYearStudentList, InternStudentList ,Department
from django.utils import timezone
from rest_framework import status
from advisors.models import Advisor
from rest_framework.exceptions import NotAuthenticated, NotFound
from rest_framework.permissions import AllowAny
from .models import Student
from django.core.exceptions import ValidationError
from telegram_bot.models import OTPVerification
from datetime import timedelta
from internships.models import Company, InternshipHistory
import os
import requests


class StudentRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        university_id = request.data.get("university_id")
        phone_number = request.data.get("phone_number")
        telegram_id = request.data.get("telegram_id")
        otp_code = request.data.get("otp_code")

        if not all([university_id, phone_number, telegram_id, otp_code]):
            return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

        if not self.verify_otp(university_id, otp_code):
            return Response({
                "OTPVerified": False,
                "error": "OTP verification failed or locked."
            }, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Get the latest department (or filter by logic you prefer)
        department = Department.objects.order_by("-internship_end").first()
        if not department or department.internship_start >= department.internship_end:
            return Response({
                "error": "The internship department calendar is invalid."
            }, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Get third-year student record
        third_year_student = ThirdYearStudentList.objects.filter(university_id=university_id).first()
        if not third_year_student:
            return Response({
                "error": "Student not found in third-year database."
            }, status=status.HTTP_404_NOT_FOUND)

        # ✅ Create or update Student
        student, _ = Student.objects.update_or_create(
            university_id=third_year_student.university_id,
            defaults={
                "full_name": third_year_student.full_name,
                "institutional_email": third_year_student.institutional_email,
                "phone_number": phone_number,
                "telegram_id": telegram_id,
                "status": "Pending",
                "assigned_advisor": None,
                "otp_verified": True,
                "department": department
            }
        )

        # ✅ Add to InternStudentList
        InternStudentList.objects.update_or_create(
            student=third_year_student
        )

        return Response({
            "message": f"🎉 Congratulations {student.full_name}! You have successfully registered! 🎉\nNow you can start using the mini app. 🚀\n\nWelcome to the AAU Internship System! 🏆\n\n👉 [Start using the mini app](https://internship-mini-app.vercel.app/) 👈",
            "OTPVerified": True,
        }, status=status.HTTP_201_CREATED)

    def verify_otp(self, university_id, otp_code):
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

    upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{path_in_bucket}"
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": file.content_type,  # Use the file's actual MIME type
        "x-upsert": "true"
    }

    try:
        # Read file content in binary mode
        file_content = file.read()
        
        # Upload raw bytes with correct Content-Type
        response = requests.put(  # Use PUT instead of POST for better reliability
            upload_url,
            headers=headers,
            data=file_content  # Send raw binary data
        )

        if response.status_code not in [200, 201]:
            raise Exception(f"Upload failed: {response.status_code} - {response.text}")

        # Return public URL
        return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{path_in_bucket}"

    except Exception as e:
        raise Exception(f"Error uploading to Supabase: {str(e)}")



class InternshipOfferLetterUploadView(generics.CreateAPIView):
    serializer_class = InternshipOfferLetterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Extract the telegram_id and document from the request
        telegram_id = serializer.validated_data.get('telegram_id')
        uploaded_file = request.FILES.get('document')

        # Ensure the file is present
        if not uploaded_file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Find the student using the telegram_id
        student = Student.objects.filter(telegram_id=telegram_id).first()
        if not student:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check if the student has an assigned advisor
        if not student.assigned_advisor:
            return Response({"error": "Advisor not assigned yet"}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the student doesn't already have an approved offer letter
        if InternshipOfferLetter.objects.filter(student=student, advisor_approved='Approved').exists():
            return Response({"error": "Approved offer letter already exists"}, status=status.HTTP_400_BAD_REQUEST)

        # Try to associate the student with the correct company
        try:
            # In this case, you're assuming the company is linked with the student's telegram_id.
            company = student.company  # Adjust this logic if needed
            if not company:
                return Response({"error": "Company not found for the student"}, status=status.HTTP_404_NOT_FOUND)

            # Prepare the file upload path
            filename = os.path.basename(uploaded_file.name)
            path = f"offer_letters/{telegram_id}/{filename}"

            # Upload the file and get the file URL
            file_url = upload_to_supabase(uploaded_file, path)

            # Create the offer letter
            offer_letter = InternshipOfferLetter.objects.create(
                student=student,
                company=company,  # Link the company to the student
                document_url=file_url
            )

            return Response({
                "message": "✅ Offer letter submitted successfully!",
                "details": f"Company: {company.name}",
                "status": "Pending advisor approval",
                "document_url": file_url
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
        uploaded_file = request.FILES.get('document')

        # ✅ Retrieve the student by telegram_id
        student = Student.objects.filter(telegram_id=telegram_id).first()
        if not student:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # ✅ Check if offer letter is approved
        offer_letter = InternshipOfferLetter.objects.filter(student=student).first()
        if not offer_letter or offer_letter.advisor_approved != 'Approved':
            return Response({"error": "Advisor approval required before submitting reports."}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Get department config
        required_reports = student.department.required_reports_count
        interval_days = student.department.report_submission_interval_days

        # ✅ Existing reports
        existing_reports = InternshipReport.objects.filter(student=student)

        # ✅ Report number check
        if existing_reports.filter(report_number=report_number).exists():
            return Response({"error": f"Report {report_number} already submitted"}, status=status.HTTP_400_BAD_REQUEST)

        expected_report = existing_reports.count() + 1
        if report_number != expected_report:
            return Response({
                "error": f"Expected report #{expected_report} next",
                "current_progress": f"{existing_reports.count()}/{required_reports} reports submitted"
            }, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Enforce report submission interval logic
        today = timezone.now().date()
        if existing_reports.exists():
            last_report = existing_reports.order_by('-report_number').first()
            last_upload_date = last_report.created_at.date()  # Make sure your model has this field
            days_since_last = (today - last_upload_date).days
            if days_since_last < interval_days:
                return Response({
                    "error": f"Report {report_number} cannot be submitted yet.",
                    "hint": f"Wait {interval_days - days_since_last} more day(s).",
                    "last_uploaded": last_upload_date,
                    "interval_days": interval_days
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # First report check: ensure internship has started
            if today < student.start_date:
                return Response({
                    "error": "Internship has not officially started yet.",
                    "start_date": student.start_date
                }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # ✅ Upload file
            filename = os.path.basename(uploaded_file.name)
            path = f"reports/{telegram_id}/{filename}"
            file_url = upload_to_supabase(uploaded_file, path)

            # ✅ Save report
            InternshipReport.objects.create(
                student=student,
                report_number=report_number,
                document_url=file_url
            )

            progress = f"{report_number}/{required_reports} reports submitted"
            remaining = required_reports - report_number

            response_data = {
                "message": f"📘 Report {report_number} submitted successfully!",
                "progress": progress,
                "remaining_reports": remaining,
                "company": offer_letter.company.name if offer_letter else None,
                "document_url": file_url
            }

            # ✅ Final report logic (when the last report is submitted)
            if report_number == required_reports:
                student.status = "Completed"
                student.save()

                # ✅ Create InternshipHistory object when the internship is completed
                if report_number == required_reports:
                    InternshipHistory.objects.create(
                        student=student,
                        company=offer_letter.company,  # You can adjust this based on your model's relations Assuming you have a field for the year
                        start_date=student.start_date,
                        end_date=today  # End date will be the current date when the last report is submitted
                    )

                # Notify via Telegram bot
                if telegram_id:
                    try:
                        requests.post("https://is-internship-tracking-bot.onrender.com/update-status", json={
                            "telegram_id": telegram_id,
                            "status": "Completed"
                        })
                    except requests.RequestException as e:
                        print(f"Failed to notify bot for {student.full_name}: {e}")

                response_data["status"] = "Completed"
                response_data["message"] += " 🎉 Internship completed!"

            return Response(response_data, status=status.HTTP_201_CREATED)

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

        response_data = {
            "student_name": student.full_name,
            "advisor_name": advisor_name,
            "offer_letter": {
                "uploaded": bool(offer),
                "approved": offer.advisor_approved if offer else False,
                "company": offer.company.name if offer else None,
                "document": offer.document_url if offer else None  # ✅ Use public Supabase URL
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

        # Get the report amount from the student's department
        report_amount = student.department.required_reports_count if student.department else 0

        # Use the actual report_amount for the loop
        for i in range(1, report_amount + 1):
            report = existing_reports.get(i)
            reports.append({
                "report_number": i,
                "uploaded": bool(report),
                "document": report.document_url if report else None
            })

        return Response({
            "student_name": student.full_name,
            "advisor_name": f"{student.assigned_advisor.first_name} {student.assigned_advisor.last_name}" if student.assigned_advisor else None,
            "report_amount": report_amount,
            "reports": reports
        })

