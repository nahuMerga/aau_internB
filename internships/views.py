from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Count
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from apscheduler.schedulers.background import BackgroundScheduler
from students.models import Student, InternshipOfferLetter, InternshipReport
from advisors.models import Advisor
from students.serializers import StudentSerializer, InternshipOfferLetterSerializer, InternshipReportSerializer
from advisors.serializers import AdvisorSerializer
from internships.serializers import CompanySerializer
from .models import Company, ThirdYearStudentList # Make sure InternshipPeriod is imported from current app
import pandas as pd
from utils.generate_email import generate_email
from utils.get_next_available_advisor import get_next_available_advisor
from django.db import models  # Add this import to fix the error
from .models import InternshipHistory
from .serializers import InternshipHistorySerializer
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from background_task import background



class AdminStudentsListView(generics.ListAPIView):
    """Admin can view all students"""
    serializer_class = StudentSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        queryset = Student.objects.all()

        for student in queryset:
            student.department_name = student.department.name if student.department else None

        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        for student_data in response.data:
            student_data['department'] = student_data.get('department', {}).get('name', None)

            student_id = student_data.get('id')
            try:
                offer_letter = InternshipOfferLetter.objects.get(student_id=student_id)
                student_data['company_name'] = offer_letter.company_name
            except InternshipOfferLetter.DoesNotExist:
                student_data['company_name'] = None

        return response


class AdminAdvisorsListView(generics.ListAPIView):
    """Admin can view all advisors"""
    serializer_class = AdvisorSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Advisor.objects.all()

class AssignAdvisorView(APIView):
    """Admin assigns students to advisors manually using student university_id and advisor username"""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        university_id = request.data.get("university_id")
        advisor_username = request.data.get("advisor_username")

        student = get_object_or_404(Student, university_id=university_id)
        advisor = get_object_or_404(Advisor, user__username=advisor_username)

        student.assigned_advisor = advisor
        student.save()

        return Response({"message": "Student assigned to advisor successfully"}, 
            status=status.HTTP_200_OK)

def assign_students_to_advisors():
    """Helper function for auto-assigning students to advisors"""
    pass

class AutoAssignAdvisorsView(APIView):
    """Triggers auto assignment manually from frontend"""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        assign_students_to_advisors()
        return Response({"message": "Automatic advisor assignment triggered"}, 
            status=status.HTTP_200_OK)


class CompanyListCreateView(generics.ListCreateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

    def get_permissions(self):
        if self.request.method == 'GET' and 'telegram_id' not in self.request.query_params:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def get(self, request, *args, **kwargs):
        telegram_id = request.query_params.get('telegram_id')
        
        if not telegram_id:
            return self.list(request, *args, **kwargs)
            
        try:
            company = Company.objects.get(telegram_id=telegram_id)
            return Response({
                "exists": True,
                "survey_completed": True,
                "can_fill_survey": False,
                "company": CompanySerializer(company).data,
                "message": "Company survey already submitted"
            }, status=status.HTTP_200_OK)
        except Company.DoesNotExist:
            try:
                student = Student.objects.get(telegram_id=telegram_id)
                advisor = student.assigned_advisor
                expected_reports = advisor.number_of_expected_reports
                required_report_number = expected_reports - 1

                report_exists = InternshipReport.objects.filter(
                    student=student,
                    report_number=required_report_number
                ).exists()
                
                return Response({
                    "exists": False,
                    "survey_completed": False,
                    "can_fill_survey": report_exists,
                    "message": "Company survey not submitted yet",
                    "requirements_met": {
                        "report_submitted": report_exists,
                        "missing_requirements": [] if report_exists else [f"Report {required_report_number}"]
                    }
                }, status=status.HTTP_200_OK)
                
            except Student.DoesNotExist:
                return Response({
                    "exists": False,
                    "survey_completed": False,
                    "can_fill_survey": False,
                    "message": "Student not found with this telegram ID",
                    "requirements_met": {
                        "report_submitted": False,
                        "missing_requirements": ["Student record"]
                    }
                }, status=status.HTTP_404_NOT_FOUND)

    def create(self, request, *args, **kwargs):
        telegram_id = request.data.get("telegram_id")

        if not telegram_id:
            return Response(
                {"error": "telegram_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if Company.objects.filter(telegram_id=telegram_id).exists():
            return Response(
                {"error": "A company with this telegram_id has already been submitted."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            student = Student.objects.get(telegram_id=telegram_id)
            advisor = student.assigned_advisor
            expected_reports = advisor.number_of_expected_reports
            required_report_number = expected_reports - 1

            report_exists = InternshipReport.objects.filter(
                student=student, 
                report_number=required_report_number
            ).exists()
            
            if not report_exists:
                return Response(
                    {"error": f"Cannot submit company survey until Report {required_report_number} is submitted."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Student.DoesNotExist:
            return Response(
                {"error": "Student with this telegram_id not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            with transaction.atomic():
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                company = serializer.save()

                return Response(
                    {
                        "message": "Company submitted successfully.",
                        "company": CompanySerializer(company).data
                    },
                    status=status.HTTP_201_CREATED
                )

        except IntegrityError:
            return Response(
                {"error": "Database integrity error. Possibly duplicate entry."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@background(schedule=1)
def notify_advisor_async(advisor_id):
    try:
        # Get the advisor (which is related to the User model)
        advisor = Advisor.objects.select_related('user').get(id=advisor_id)
        
        # Get the email of the associated User model
        advisor_email = advisor.user.email

        # Get the students assigned to the advisor
        students = ThirdYearStudentList.objects.filter(assigned_advisor=advisor)

        if not students.exists():
            return

        # Prepare the list of students to send in the email
        student_lines = [f"{s.full_name} (ID: {s.university_id})" for s in students]
        student_list_text = "\n".join(student_lines)

        # Prepare the email content
        subject = "AAU Internship – Your Assigned Students"
        message = (
            f"Dear {advisor.first_name},\n\n"
            f"You have been assigned the following students:\n\n"
            f"{student_list_text}\n\n"
            f"Best regards,\nAAU Internship Team"
        )
        from_email = "aau57.sis@gmail.com"  # Your email address here
        recipient_list = [advisor_email]

        # Send the email
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        print(f"Email sent to {advisor_email} successfully.")

    except ObjectDoesNotExist:
        print(f"Error: Advisor with ID {advisor_id} does not exist.")
    except Exception as e:
        print(f"Error sending email to {advisor_id}: {str(e)}")

class UploadStudentExcelView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, format=None):
        excel_file = request.FILES.get('file')
        if not excel_file:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = pd.read_excel(excel_file)
            required_columns = {'university_id', 'full_name'}
            if not required_columns.issubset(df.columns):
                return Response({
                    "error": f"Missing columns. Required: {required_columns}"
                }, status=status.HTTP_400_BAD_REQUEST)

            created_students = []
            advisors = Advisor.objects.all().annotate(current_load=models.Count('thirdyearstudentlist'))

            for _, row in df.iterrows():
                university_id = str(row['university_id']).strip()[:20]
                full_name = str(row['full_name']).strip()

                if ThirdYearStudentList.objects.filter(university_id=university_id).exists():
                    continue

                email = generate_email(full_name, university_id)
                advisor = get_next_available_advisor()
                if not advisor:
                    return Response({"error": "No available advisor."}, status=status.HTTP_400_BAD_REQUEST)

                student = ThirdYearStudentList.objects.create(
                    university_id=university_id,
                    full_name=full_name,
                    institutional_email=email,
                    assigned_advisor=advisor
                )

                created_students.append({
                    "university_id": university_id,
                    "full_name": full_name,
                    "email": email,
                    "advisor": advisor.first_name
                })

            for advisor in Advisor.objects.all():
                notify_advisor_async(advisor.id)

            return Response({
                "message": f"{len(created_students)} students uploaded successfully.",
                "data": created_students
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InternshipHistoryListView(generics.ListAPIView):
    serializer_class = InternshipHistorySerializer
    permission_classes = [permissions.IsAdminUser] 
    
    def get_queryset(self):
        year = self.request.query_params.get('year', None)
        
        if year:
            return InternshipHistory.objects.filter(year=year)
        
        return InternshipHistory.objects.all()