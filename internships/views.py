from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Count
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from apscheduler.schedulers.background import BackgroundScheduler
from students.models import Student
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


class AdminStudentsListView(generics.ListAPIView):
    """Admin can view all students"""
    serializer_class = StudentSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        queryset = Student.objects.all()

        # Modify the queryset to include only necessary department information
        for student in queryset:
            # Manually add the department name to each student object
            student.department_name = student.department.name if student.department else None

        return queryset

    def list(self, request, *args, **kwargs):
        # Call the original list method to get the serialized data
        response = super().list(request, *args, **kwargs)

        # Modify the response to include only the department name
        for student_data in response.data:
            # Ensure department data is overridden to only show the name
            student_data['department'] = student_data.get('department', {}).get('name', None)

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
    # Implement your assignment logic here
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
    permission_classes = [permissions.AllowAny]  # Or IsAuthenticated if needed

    def create(self, request, *args, **kwargs):
        # Pass telegram_id along with company data to the serializer
        telegram_id = request.data.get("telegram_id")

        if not telegram_id:
            return Response({"error": "telegram_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Use the serializer to validate and create the company
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # The company will be created and linked to the student in the serializer
        company = serializer.save()

        return Response({
            "message": "Company submitted and linked successfully.",
            "company": CompanySerializer(company).data
        }, status=status.HTTP_201_CREATED)

class UploadStudentExcelView(APIView):
    permission_classes = [permissions.AllowAny]  # Ensure only admin can upload the file

    def post(self, request, format=None):
        excel_file = request.FILES.get('file')
        if not excel_file:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Read the Excel file into a pandas dataframe
            df = pd.read_excel(excel_file)

            required_columns = {'university_id', 'full_name'}
            if not required_columns.issubset(set(df.columns)):
                return Response({
                    "error": f"Missing required columns. Required: {required_columns}"
                }, status=status.HTTP_400_BAD_REQUEST)

            created_students = []

            # Get a list of all advisors and their current load
            advisors = Advisor.objects.all().annotate(current_load=models.Count('thirdyearstudentlist'))

            for _, row in df.iterrows():
                university_id = str(row['university_id']).strip()[:20]
                full_name = str(row['full_name']).strip()

                if len(university_id) > 20:
                    return Response({"error": f"University ID '{university_id}' is too long. Max length is 20 characters."}, status=status.HTTP_400_BAD_REQUEST)

                if ThirdYearStudentList.objects.filter(university_id=university_id).exists():
                    continue

                email = generate_email(full_name, university_id)
                advisor = get_next_available_advisor()

                if not advisor:
                    return Response({"error": "No available advisor found."}, status=status.HTTP_400_BAD_REQUEST)

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
                    "advisor": advisor.first_name if advisor else None
                })

            # ✅ Notify each advisor by email (use advisor.user.email)
            for advisor in Advisor.objects.select_related('user'):
                students = ThirdYearStudentList.objects.filter(assigned_advisor=advisor)
                if not students.exists():
                    continue

                student_lines = [
                    f"{s.full_name} (ID: {s.university_id})" for s in students
                ]
                student_list_text = "\n".join(student_lines)

                try:
                    send_mail(
                        subject="AAU Internship – Your Assigned Students",
                        message=(
                            f"Dear {advisor.first_name},\n\n"
                            f"You have been assigned the following students for internship supervision:\n\n"
                            f"{student_list_text}\n\n"
                            f"Please prepare to guide them during the internship period.\n\n"
                            f"Best regards,\nAAU Internship Team"
                        ),
                        from_email="aau57.sis@gmail.com",
                        recipient_list=[advisor.user.email],  # ✅ Fixed here
                        fail_silently=False,
                    )
                except Exception as e:
                    print(f"Failed to email advisor {advisor.user.email}: {str(e)}")

            return Response({
                "message": f"{len(created_students)} students uploaded successfully.",
                "data": created_students
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class InternshipHistoryListView(generics.ListAPIView):
    serializer_class = InternshipHistorySerializer
    permission_classes = [permissions.IsAdminUser] # Admin permission only
    
    def get_queryset(self):
        # Get 'year' from query params, or default to None if not provided
        year = self.request.query_params.get('year', None)
        
        # Filter by year if it's provided
        if year:
            return InternshipHistory.objects.filter(year=year)
        
        # If no year is provided, return all records
        return InternshipHistory.objects.all()