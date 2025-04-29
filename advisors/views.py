from django.contrib.auth import authenticate
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from advisors.models import Advisor
from students.models import Student, InternshipOfferLetter,InternshipReport
from internships.serializers import CompanySerializer
from students.serializers import StudentSerializer, InternshipReportSerializer, InternshipOfferLetterSerializer, InternshipReportReadSerializer , InternshipOfferLetterReadSerializer
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from .serializers import AdvisorRegistrationSerializer, AdvisorSerializer, UserSerializer, AdvisorProfileSerializer, AdvisorSettingsSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.http import Http404
from django.utils import timezone
from datetime import timedelta
import requests  # for making HTTP requests
import pandas as pd
import random
import string
from django.core.mail import send_mail
from rest_framework.exceptions import ValidationError
from django.contrib.auth import password_validation



class UpdateAdvisorProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, user):
        try:
            return Advisor.objects.get(user=user)
        except Advisor.DoesNotExist:
            raise Http404

    def get(self, request, *args, **kwargs):
        advisor = self.get_object(request.user)
        serializer = AdvisorProfileSerializer(advisor)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        advisor = self.get_object(request.user)

        # Check if username needs to be updated
        username = request.data.get('username', None)
        password = request.data.get('password', None)

        if username:
            # Ensure the new username is unique and valid
            if User.objects.filter(username=username).exists():
                return Response({"error": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)
            advisor.user.username = username

        # Handle password change if it's provided in the request
        if password:
            # Validate the password using Django's password validation system
            try:
                password_validation.validate_password(password)
            except ValidationError as e:
                return Response({"error": e.messages}, status=status.HTTP_400_BAD_REQUEST)
            
            # Set the new password securely
            advisor.user.set_password(password)

        # Update other profile information
        serializer = AdvisorProfileSerializer(advisor, data=request.data, partial=True)
        if serializer.is_valid():
            # Save the changes, including the username and password update if any
            advisor.user.save()  # Save the user object (to persist username change)
            advisor.user.set_password(password) if password else None  # Update password if present
            serializer.save()

            # If password is changed, the user needs to be logged out and reauthenticated
            if password:
                return Response({"message": "Profile updated. Please log in with your new password."}, status=status.HTTP_200_OK)

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Utility function to generate a random password
def generate_password():
    """Generate a random password"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

# View to handle advisor bulk registration from Excel
class AdvisorRegistrationView(APIView):
    permission_classes = [AllowAny]  # Admin will use this API
    
    def post(self, request):
        excel_file = request.FILES.get('file')
        if not excel_file:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Read the Excel file into a pandas dataframe
            df = pd.read_excel(excel_file)

            # Check if the necessary columns are present in the file
            required_columns = {'advisor_name', 'email'}
            if not required_columns.issubset(set(df.columns)):
                return Response({
                    "error": f"Missing required columns. Required: {required_columns}"
                }, status=status.HTTP_400_BAD_REQUEST)

            failed_emails = []
            successful_emails = []

            # Iterate over the rows in the Excel file
            for _, row in df.iterrows():
                advisor_name = str(row['advisor_name']).strip()
                email = str(row['email']).strip()

                # Ensure the email is valid and doesn't already exist in the system
                if User.objects.filter(email=email).exists():
                    failed_emails.append(email)
                    continue
                
                username = advisor_name.replace(" ", "").lower()  # Simplified username from name
                password = generate_password()  # Generate a random password

                try:
                    # Create the user
                    user = User.objects.create_user(username=username, email=email, password=password)
                    user.is_active = True  # Make the user active
                    user.save()

                    # Create the advisor profile in the Advisor model
                    advisor = Advisor.objects.create(user=user)
                    # Send an email with the generated credentials to the advisor
                    send_mail(
                        subject="Your Advisor Account Credentials",
                        message=f"Hello {advisor_name},\n\nYour account has been created.\nUsername: {username}\nPassword: {password}\n\nPlease log in and update your password immediately.",
                        from_email="admin@yourdomain.com",  # Update with your real email
                        recipient_list=[email],
                        fail_silently=False,
                    )

                    successful_emails.append(email)

                except Exception as e:
                    failed_emails.append(email)
                    print(f"Error creating advisor for {email}: {str(e)}")

            return Response({
                'successful_emails': successful_emails,
                'failed_emails': failed_emails,
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token)
            })
        return Response({'error': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
        
class AdvisorStudentsView(APIView):
    """
    Get a list of students assigned to the logged-in advisor,
    including offer letter, reports, and dashboard stats.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        advisor = getattr(request.user, "advisor", None)
        if not advisor:
            return Response({"error": "User is not an advisor"}, status=status.HTTP_403_FORBIDDEN)

        students = Student.objects.filter(assigned_advisor=advisor)

        student_data = []
        total_assigned_students = students.count()
        pending_approval_count = 0
        reports_to_review_count = 0

        for student in students:
            offer_letter = InternshipOfferLetter.objects.filter(student=student).first()
            reports = InternshipReport.objects.filter(student=student)

            # Count pending advisor approvals for offer letter
            if offer_letter and offer_letter.advisor_approved == "Pending":
                pending_approval_count += 1

            # Count how many reports the student has (to review = all of them for now)
            reports_to_review_count += reports.count()

            student_data.append({
                "id": student.id,
                "university_id": student.university_id,
                "full_name": student.full_name,
                "institutional_email": student.institutional_email,
                "phone_number": student.phone_number,
                "telegram_id": student.telegram_id,  # ← Added this line
                "status": student.status,
                "start_date": student.start_date,
                "end_date": student.end_date,
                "department": student.department.name,
                "company_name": offer_letter.company_name if offer_letter else None,  # ✅ Add this line
                "offer_letter": InternshipOfferLetterReadSerializer(offer_letter).data if offer_letter else None,
                "internship_reports": InternshipReportReadSerializer(reports, many=True).data
            })


        response_data = {
            "students": student_data,
            "stats": {
                "assigned_students": total_assigned_students,
                "pending_approval": pending_approval_count,
                "reports_to_review": reports_to_review_count
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)


class StudentDetailView(APIView):
    """Retrieve details of a specific student using university_id"""
    permission_classes = [AllowAny]

    def get(self, request, university_id):
        # Automatically format university_id (UGR102517 → UGR/1025/17)
        if len(university_id) == 9:  # Assuming format is fixed
            formatted_id = f"{university_id[:3]}/{university_id[3:7]}/{university_id[7:]}"
        else:
            return Response({"error": "Invalid university_id format"}, status=status.HTTP_400_BAD_REQUEST)

        advisor = getattr(request.user, "advisor", None)
        if not advisor:
            return Response({"error": "User is not an advisor"}, status=status.HTTP_403_FORBIDDEN)

        student = get_object_or_404(Student, university_id=formatted_id, assigned_advisor=advisor)

        # Get related documents
        offer_letter = InternshipOfferLetter.objects.filter(student=student).first()
        reports = InternshipReport.objects.filter(student=student)

        # Serialize response
        student_data = StudentSerializer(student).data
        student_data["telegram_id"] = student.telegram_id
        
        # Handle internship offer letter details
        if offer_letter:
            student_data["internship_offer_letter"] = {
                "company_name": offer_letter.company_name if offer_letter else None,  # ✅ Add this line
                "document_url": offer_letter.document_url,  # Add URL for the offer letter document
                "advisor_approved": offer_letter.advisor_approved,
                "approval_date": offer_letter.approval_date,
                "submission_date": offer_letter.submission_date,
                # Removed the company field as it's no longer in the model
            }
        else:
            student_data["internship_offer_letter"] = None

        # Handle internship reports details
        student_data["internship_reports"] = []
        for report in reports:
            student_data["internship_reports"].append({
                "report_number": report.report_number,
                "document_url": report.document_url,  # Add URL for the report document
                "submission_date": report.submission_date,
                "created_at": report.created_at,
            })

        # Additional student details
        student_data["department"] = student.department.name  # Include department name only

        return Response(student_data, status=status.HTTP_200_OK)




class ApproveOfferLetterView(APIView):
    """Approve or reject an internship offer letter using the student's university_id"""
    permission_classes = [IsAuthenticated]

    def put(self, request):
        university_id = request.data.get("university_id")
        status_value = request.data.get("status")

        if status_value not in ["Approved", "Rejected"]:
            return Response({"error": "Invalid status value"}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user

        # Superuser can manage any offer letter
        if user.is_superuser:
            offer_letter = get_object_or_404(InternshipOfferLetter, student__university_id=university_id)
        else:
            advisor = getattr(user, "advisor", None)
            if not advisor:
                return Response({"error": "User is not an advisor"}, status=status.HTTP_403_FORBIDDEN)

            offer_letter = get_object_or_404(
                InternshipOfferLetter,
                student__university_id=university_id,
                student__assigned_advisor=advisor
            )

        student = offer_letter.student

        # Fetch internship duration from the department the student belongs to
        department = student.department
        if department:
            internship_duration_days = department.internship_duration_weeks * 7  # Convert weeks to days
        else:
            return Response({"error": "Department information is missing for this student"}, status=status.HTTP_400_BAD_REQUEST)

        # Handling approve/reject logic
        if status_value == "Approved":
            now = timezone.now().date()

            # Set approval info
            offer_letter.advisor_approved = "Approved"
            offer_letter.approval_date = timezone.now()
            offer_letter.save()

            # Set student internship duration dynamically
            student.start_date = now
            student.end_date = now + timedelta(days=internship_duration_days)  # Use dynamic duration
            student.status = "Ongoing"
            student.save()

            # Send notification via POST request
            if student.telegram_id:
                payload = {
                    "telegram_id": student.telegram_id,
                    "status": "Approved"
                }
                try:
                    response = requests.post(
                        "https://is-internship-tracking-bot.onrender.com/update-status",
                        json=payload
                    )
                    response.raise_for_status()  # Optional: raise error for bad status
                except requests.RequestException as e:
                    # Log this properly in production
                    print("Notification failed:", e)

            message = "Offer letter approved successfully"

        elif status_value == "Rejected":
            offer_letter.delete()
            message = "Offer letter rejected and removed from the database"

        return Response({
            "message": message,
            "student_name": student.full_name,
            "student_university_id": student.university_id
        }, status=status.HTTP_200_OK)
        
class UpdateAdvisorSettingsView(APIView):
    permission_classes = [AllowAny]

    def put(self, request):
        advisor = getattr(request.user, "advisor", None)
        if not advisor:
            return Response({"error": "User is not an advisor"}, status=status.HTTP_403_FORBIDDEN)

        serializer = AdvisorSettingsSerializer(advisor, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Advisor settings updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


