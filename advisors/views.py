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
from django.db import transaction
from internships.models import ThirdYearStudentList
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from rest_framework.throttling import ScopedRateThrottle

class UpdateAdvisorProfileView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = 'advisor'
    throttle_classes = [ScopedRateThrottle]

    def get_object(self, user):
        try:
            return Advisor.objects.get(user=user)
        except Advisor.DoesNotExist:
            raise Http404


    @method_decorator(cache_page(300))
    @method_decorator(vary_on_headers('Authorization'))
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


def generate_password(length=10):
    """Generate a secure random password"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def clean_string(value):
    """Ensure value is string, trimmed, and non-null"""
    return str(value).strip() if pd.notna(value) else ""


class AdvisorRegistrationView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'sensitive'
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "❌ No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = pd.read_excel(file)

            required_columns = {'advisor_name', 'email', 'f_name', 'l_name', 'phone_number'}
            if not required_columns.issubset(df.columns):
                return Response({
                    "error": f"❌ Missing required columns. Found: {set(df.columns)}. Required: {required_columns}"
                }, status=status.HTTP_400_BAD_REQUEST)

            failed_rows = []
            successful_emails = []

            for index, row in df.iterrows():
                try:
                    advisor_name = clean_string(row['advisor_name'])
                    email = clean_string(row['email'])
                    f_name = clean_string(row['f_name'])
                    l_name = clean_string(row['l_name'])
                    phone_number = clean_string(row['phone_number'])

                    if not all([advisor_name, email, f_name, l_name, phone_number]):
                        raise ValueError("⚠️ One or more required fields are empty.")

                    if not phone_number.isdigit():
                        raise ValueError("📵 Invalid phone number: must contain digits only.")

                    if User.objects.filter(email=email).exists():
                        raise ValueError("📧 Email already exists.")

                    # Unique username
                    base_username = advisor_name.replace(" ", "").lower()
                    username = base_username
                    counter = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1

                    password = generate_password()

                    # ✅ Register user and advisor (no atomic block)
                    user = User.objects.create_user(username=username, email=email, password=password)
                    user.is_active = True
                    user.save()

                    Advisor.objects.create(
                        user=user,
                        first_name=f_name,
                        last_name=l_name,
                        phone_number=phone_number
                    )

                    # ✅ Try to send email, but don't raise errors
                    try:
                        send_mail(
                            subject="Your Advisor Account Credentials",
                            message=(
                                f"Dear {advisor_name},\n\n"
                                f"Your advisor account has been created.\n\n"
                                f"Username: {username}\nPassword: {password}\n\n"
                                "Please login and update your password immediately."
                            ),
                            from_email="admin@yourdomain.com",
                            recipient_list=[email],
                            fail_silently=True  # Don't throw error if it fails
                        )
                    except Exception as email_error:
                        print(f"⚠️ Failed to send email to {email}: {email_error}")

                    successful_emails.append(email)

                except Exception as e:
                    failed_rows.append({
                        "row_number": index + 2,
                        "email": email,
                        "error": str(e)
                    })

            return Response({
                "✅ successful_emails": successful_emails,
                "❌ failed_rows": failed_rows,
                "summary": f"{len(successful_emails)} succeeded, {len(failed_rows)} failed"
            }, status=status.HTTP_200_OK)

        except Exception as global_error:
            return Response({
                "error": f"❌ Something went wrong while processing the file: {str(global_error)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'sensitive'
    throttle_classes = [ScopedRateThrottle]
    
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
    throttle_scope = 'advisor'
    throttle_classes = [ScopedRateThrottle]

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
    including offer letter, reports, dashboard stats, and third-year student list.
    """
    permission_classes = [AllowAny]
    throttle_scope = 'advisor'
    throttle_classes = [ScopedRateThrottle]

    @method_decorator(cache_page(3600))
    @method_decorator(vary_on_headers('Authorization'))
    def get(self, request):
        advisor = getattr(request.user, "advisor", None)
        if not advisor:
            return Response({"error": "User is not an advisor"}, status=status.HTTP_403_FORBIDDEN)

        students = Student.objects.filter(assigned_advisor=advisor)
        third_year_students = ThirdYearStudentList.objects.filter(assigned_advisor=advisor)

        student_data = []
        total_assigned_students = students.count()
        pending_approval_count = 0
        reports_to_review_count = 0

        for student in students:
            offer_letter = InternshipOfferLetter.objects.filter(student=student).first()
            reports = InternshipReport.objects.filter(student=student)

            if offer_letter and offer_letter.advisor_approved == "Pending":
                pending_approval_count += 1

            reports_to_review_count += reports.count()

            student_data.append({
                "id": student.id,
                "university_id": student.university_id,
                "full_name": student.full_name,
                "institutional_email": student.institutional_email,
                "phone_number": student.phone_number,
                "telegram_id": student.telegram_id,
                "status": student.status,
                "start_date": student.start_date,
                "end_date": student.end_date,
                "department": student.department.name,
                "company_name": offer_letter.company_name if offer_letter else None,
                "offer_letter": InternshipOfferLetterReadSerializer(offer_letter).data if offer_letter else None,
                "internship_reports": InternshipReportReadSerializer(reports, many=True).data
            })

        third_year_data = []
        for s in third_year_students:
            third_year_data.append({
                "university_id": s.university_id,
                "full_name": s.full_name,
                "institutional_email": s.institutional_email
            })

        response_data = {
            "students": student_data,
            "third_year_students": third_year_data,
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
    throttle_scope = 'advisor'
    throttle_classes = [ScopedRateThrottle]

    @method_decorator(cache_page(1800))
    @method_decorator(vary_on_headers('Authorization'))
    def get(self, request, university_id):
        if len(university_id) == 9:  # Assuming format is fixed
            formatted_id = f"{university_id[:3]}/{university_id[3:7]}/{university_id[7:]}"
        else:
            return Response({"error": "Invalid university_id format"}, status=status.HTTP_400_BAD_REQUEST)

        advisor = getattr(request.user, "advisor", None)
        if not advisor:
            return Response({"error": "User is not an advisor"}, status=status.HTTP_403_FORBIDDEN)

        student = get_object_or_404(Student, university_id=formatted_id, assigned_advisor=advisor)

        offer_letter = InternshipOfferLetter.objects.filter(student=student).first()
        reports = InternshipReport.objects.filter(student=student)

        student_data = StudentSerializer(student).data
        student_data["telegram_id"] = student.telegram_id
        
        if offer_letter:
            student_data["internship_offer_letter"] = {
                "company_name": offer_letter.company_name if offer_letter else None,
                "document_url": offer_letter.document_url,
                "advisor_approved": offer_letter.advisor_approved,
                "approval_date": offer_letter.approval_date,
                "submission_date": offer_letter.submission_date,
            }
        else:
            student_data["internship_offer_letter"] = None

        student_data["internship_reports"] = []
        for report in reports:
            student_data["internship_reports"].append({
                "report_number": report.report_number,
                "document_url": report.document_url,
                "submission_date": report.submission_date,
                "created_at": report.created_at,
            })

        student_data["department"] = student.department.name

        return Response(student_data, status=status.HTTP_200_OK)




class ApproveOfferLetterView(APIView):
    """Approve or reject an internship offer letter using the student's university_id"""
    permission_classes = [IsAuthenticated]
    throttle_scope = 'advisor'
    throttle_classes = [ScopedRateThrottle]

    def put(self, request):
        university_id = request.data.get("university_id")
        status_value = request.data.get("status")

        if status_value not in ["Approved", "Rejected"]:
            return Response({"error": "Invalid status value"}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user

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
        department = student.department

        if not department:
            return Response({"error": "Department information is missing for this student"}, status=status.HTTP_400_BAD_REQUEST)

        internship_duration_days = department.internship_duration_weeks * 7

        if status_value == "Approved":
            now = timezone.now().date()

            offer_letter.advisor_approved = "Approved"
            offer_letter.approval_date = timezone.now()
            offer_letter.save()

            student.start_date = now
            student.end_date = now + timedelta(days=internship_duration_days)
            student.status = "Ongoing"
            student.save()

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
                    response.raise_for_status()
                except requests.RequestException as e:
                    print("Notification failed:", e)

            return Response({
                "message": "Offer letter approved successfully",
                "student_name": student.full_name,
                "student_university_id": student.university_id
            }, status=status.HTTP_200_OK)

        elif status_value == "Rejected":
            telegram_id = student.telegram_id
            full_name = student.full_name
            offer_letter.delete()

            if telegram_id:
                payload = {
                    "telegram_id": telegram_id,
                    "status": "Rejected"
                }
                try:
                    response = requests.post(
                        "https://is-internship-tracking-bot.onrender.com/update-status",
                        json=payload
                    )
                    response.raise_for_status()
                except requests.RequestException as e:
                    print("Notification failed:", e)

            return Response({
                "message": "Student rejected successfully",
                "student_name": full_name
            }, status=status.HTTP_200_OK)

        
class UpdateAdvisorSettingsView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'advisor'
    throttle_classes = [ScopedRateThrottle]

    def put(self, request):
        advisor = getattr(request.user, "advisor", None)
        if not advisor:
            return Response({"error": "User is not an advisor"}, status=status.HTTP_403_FORBIDDEN)

        serializer = AdvisorSettingsSerializer(advisor, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Advisor settings updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

