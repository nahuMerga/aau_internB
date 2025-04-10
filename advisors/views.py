from django.contrib.auth import authenticate
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from advisors.models import Advisor
from students.models import Student, InternshipOfferLetter,InternshipReport
from students.serializers import StudentSerializer, InternshipReportSerializer, InternshipOfferLetterSerializer
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from .serializers import AdvisorRegistrationSerializer, AdvisorSerializer, UserSerializer, AdvisorProfileSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.http import Http404
from django.utils import timezone
from datetime import timedelta
import requests  # for making HTTP requests


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

        serializer = AdvisorProfileSerializer(advisor, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdvisorRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Register a new user and create an advisor profile, then return JWT token
        """
        # First, serialize and create the user
        user_serializer = UserSerializer(data=request.data)
        if user_serializer.is_valid():
            user = user_serializer.save()  # Save the user instance

            # Now, create the advisor profile with the user instance
            advisor_data = {
                'user': user,  # Link the advisor to the user
                'first_name': request.data.get('first_name'),
                'last_name': request.data.get('last_name'),
                'phone_number': request.data.get('phone_number')
            }
            
            advisor = Advisor.objects.create(**advisor_data) 
            advisor.save()

            refresh = RefreshToken.for_user(user) 
            access_token = refresh.access_token  

            return Response({
                'refresh': str(refresh),
                'access': str(access_token)
            }, status=status.HTTP_201_CREATED)
        
        return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
    """Get a list of students assigned to the logged-in advisor, including offer letter, reports, and dashboard stats."""
    permission_classes = [AllowAny]  # Update to IsAuthenticated if you want to enforce login

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

            # Count pending approvals
            if student.status == "pending":  # Adjust based on your actual statuses
                pending_approval_count += 1

            # Count unreviewed reports
            for report in reports:
                if not getattr(report, "is_reviewed", False):  # Adjust if field is named differently
                    reports_to_review_count += 1

            student_data.append({
                "id": student.id,
                "university_id": student.university_id,
                "full_name": student.full_name,
                "institutional_email": student.institutional_email,
                "phone_number": student.phone_number,
                "status": student.status,
                "start_date": student.start_date,
                "end_date": student.end_date,
                "student_grade": student.student_grade,
                "offer_letter": InternshipOfferLetterSerializer(offer_letter).data if offer_letter else None,
                "internship_reports": InternshipReportSerializer(reports, many=True).data
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
        student_data["internship_offer_letter"] = (
            InternshipOfferLetterSerializer(offer_letter).data if offer_letter else None
        )
        student_data["internship_reports"] = InternshipReportSerializer(reports, many=True).data
        student_data["company"] = offer_letter.company if offer_letter else None  # ✅ Added line

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

        # Handling approve/reject logic
        if status_value == "Approved":
            now = timezone.now().date()

            # ✅ Set approval info
            offer_letter.advisor_approved = "Approved"
            offer_letter.approval_date = timezone.now()
            offer_letter.save()

            # ✅ Set student internship duration
            student.start_date = now
            student.end_date = now + timedelta(days=60)  # ~2 months
            student.status = "Ongoing"
            student.save()

            # ✅ Send notification via POST request
            if student.telegram_id:
                payload = {
                    "telegram_id": student.telegram_id,
                    "status": "Approved"
                }
                try:
                    response = requests.post(
                        "https://is-internship-tracking-bot.onrender.com",
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

