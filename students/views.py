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
            
        existing_student = Student.objects.filter(university_id=university_id, otp_verified=True).first()
        if existing_student:
            return Response({
                "error": "You have already registered and verified your account.",
                "OTPVerified": True
            }, status=status.HTTP_400_BAD_REQUEST)

        department = Department.objects.order_by("-internship_end").first()
        if not department or department.internship_start >= department.internship_end:
            return Response({
                "error": "The internship department calendar is invalid."
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
                "assigned_advisor": None,
                "otp_verified": True,
                "department": department
            }
        )

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
        file_content = file.read()
        
       
        response = requests.put( 
            upload_url,
            headers=headers,
            data=file_content  
        )

        if response.status_code not in [200, 201]:
            raise Exception(f"Upload failed: {response.status_code} - {response.text}")

        
        return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{path_in_bucket}"

    except Exception as e:
        raise Exception(f"Error uploading to Supabase: {str(e)}")



def validate_file_format(file):
    """Improved file validation with better error messages"""
    if not file:
        raise ValidationError("Please select a file to upload.")
    
    if file.size == 0:
        raise ValidationError("The file you uploaded is empty. Please upload a valid document.")
    
    valid_formats = ['pdf', 'docx', 'doc']
    file_extension = file.name.split('.')[-1].lower()
    
    if not file_extension:
        raise ValidationError("The file has no extension. Please upload a PDF or Word document.")
    
    if file_extension not in valid_formats:
        raise ValidationError(
            "Unsupported file type. "
            "Please upload your report in one of these formats: "
            "PDF (.pdf), Word (.docx or .doc)."
        )

class InternshipOfferLetterUploadView(generics.CreateAPIView):
    serializer_class = InternshipOfferLetterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        telegram_id = serializer.validated_data.get('telegram_id')
        uploaded_file = request.FILES.get('document')
        company_name = request.data.get('company_name')  # ✅ Extract company_name from request


        if not uploaded_file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        student = Student.objects.filter(telegram_id=telegram_id).first()
        if not student:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

        if not student.assigned_advisor:
            return Response({"error": "Advisor not assigned yet"}, status=status.HTTP_400_BAD_REQUEST)

    
        if InternshipOfferLetter.objects.filter(student=student, advisor_approved='Approved').exists():
            return Response({"error": "Approved offer letter already exists"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            
            filename = validate_file_format(uploaded_file)

          
            path = f"offer_letters/{telegram_id}/{filename}"

           
            file_url = upload_to_supabase(uploaded_file, path)

          
            offer_letter = InternshipOfferLetter.objects.create(
                student=student,
                document_url=file_url,
                company_name=company_name  # ✅ Save company name
            )

            return Response({
                "message": "✅ Offer letter submitted successfully!",
                "status": "Pending advisor approval",
                "document_url": file_url
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
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

       
        if not uploaded_file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        student = Student.objects.filter(telegram_id=telegram_id).first()
        if not student:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

        advisor = student.assigned_advisor
        if not advisor:
            return Response({"error": "No advisor assigned to this student"}, status=status.HTTP_400_BAD_REQUEST)

       
        required_reports = advisor.number_of_expected_reports
        interval_days = advisor.report_submission_interval_days

        existing_reports = InternshipReport.objects.filter(student=student)

        if existing_reports.filter(report_number=report_number).exists():
            return Response({"error": f"Report {report_number} already submitted"}, status=status.HTTP_400_BAD_REQUEST)

        expected_report = existing_reports.count() + 1
        if report_number != expected_report:
            return Response({
                "error": f"Expected report #{expected_report} next",
                "current_progress": f"{existing_reports.count()}/{required_reports} reports submitted"
            }, status=status.HTTP_400_BAD_REQUEST)

        today = timezone.now().date()
        if existing_reports.exists():
            last_report = existing_reports.order_by('-report_number').first()
            last_upload_date = last_report.created_at.date()
            days_since_last = (today - last_upload_date).days
            if days_since_last < interval_days:
                return Response({
                    "error": f"Report {report_number} cannot be submitted yet.",
                    "hint": f"Wait {interval_days - days_since_last} more day(s).",
                    "last_uploaded": last_upload_date,
                    "interval_days": interval_days
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            if today < student.start_date:
                return Response({
                    "error": "Internship has not officially started yet.",
                    "start_date": student.start_date
                }, status=status.HTTP_400_BAD_REQUEST)

        try:
           
            filename = validate_file_format(uploaded_file)

          
            path = f"reports/{telegram_id}/{filename}"
            file_url = upload_to_supabase(uploaded_file, path)

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
                "document_url": file_url 
            }

            if report_number == required_reports:
                student.status = "Completed"
                student.save()

               
                company = Company.objects.filter(telegram_id=telegram_id).first()

                InternshipHistory.objects.create(
                    student=student,
                    company=company,
                    start_date=student.start_date,
                    end_date=today
                )

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

        except ValidationError as e:
            return Response({
                "error": "Document upload failed",
                "details": str(e),
                "solution": "Please check your file and try again with a valid document"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "error": "Unexpected error occurred",
                "details": "We couldn't process your document upload",
                "solution": "Please try again later or contact support"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        

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
                "document": offer.document_url if offer else None 
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

        advisor = student.assigned_advisor
        if not advisor:
            return Response({"error": "No advisor assigned to this student"}, status=status.HTTP_400_BAD_REQUEST)

        existing_reports = {r.report_number: r for r in InternshipReport.objects.filter(student=student)}
        report_amount = advisor.number_of_expected_reports

        reports = []
        for i in range(1, report_amount + 1):
            report = existing_reports.get(i)
            reports.append({
                "report_number": i,
                "uploaded": bool(report),
                "document": report.document_url if report else None
            })

        return Response({
            "student_name": student.full_name,
            "advisor_name": f"{advisor.first_name} {advisor.last_name}",
            "report_amount": report_amount,
            "submission_interval_days": advisor.report_submission_interval_days,
            "reports": reports
        })
