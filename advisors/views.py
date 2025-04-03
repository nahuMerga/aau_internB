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
    """Get a list of students assigned to the logged-in advisor, including their offer letter & reports"""
    permission_classes = [AllowAny]  # No authentication enforced

    def get(self, request):
        advisor = getattr(request.user, "advisor", None)
        if not advisor:
            return Response({"error": "User is not an advisor"}, status=status.HTTP_403_FORBIDDEN)

        students = Student.objects.filter(assigned_advisor=advisor)

        # Serialize with nested internship details
        student_data = []
        for student in students:
            offer_letter = InternshipOfferLetter.objects.filter(student=student).first()
            reports = InternshipReport.objects.filter(student=student)

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

        return Response(student_data, status=status.HTTP_200_OK)


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

        return Response(student_data, status=status.HTTP_200_OK)



class ApproveOfferLetterView(APIView):
    """Approve or reject an internship offer letter using the student's university_id"""
    permission_classes = [IsAuthenticated]

    def put(self, request):
        # It seems like there is a typo in your code snippet. The variable `univer` is not defined or
        # used anywhere in the provided code. If you could provide more context or clarify where
        # `univer` is supposed to be used, I would be happy to help you with that specific part of the
        # code.
        university_id = request.data.get("university_id")
        status_value = request.data.get("status")

        if status_value not in ["Approved", "Rejected"]:
            return Response({"error": "Invalid status value"}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user

        # Superusers can approve/reject any offer letter
        if user.is_superuser:
            offer_letter = get_object_or_404(InternshipOfferLetter, student__university_id=university_id)
        else:
            advisor = getattr(user, "advisor", None)
            if not advisor:
                return Response({"error": "User is not an advisor"}, status=status.HTTP_403_FORBIDDEN)

            # Only fetch offer letters of the advisor's assigned students
            offer_letter = get_object_or_404(
                InternshipOfferLetter,
                student__university_id=university_id,
                student__assigned_advisor=advisor
            )

        # Convert "Approved"/"Rejected" to Boolean
        offer_letter.advisor_approved = status_value == "Approved"

        # Set approval date if approved
        if status_value == "Approved":
            offer_letter.approval_date = timezone.now()
        else:
            offer_letter.approval_date = None  # Reset approval date if rejected

        offer_letter.save()

        return Response({
            "message": f"Offer letter {status_value.lower()} successfully",
            "student_name": offer_letter.student.full_name,
            "student_university_id": university_id,
            "advisor_approved": offer_letter.advisor_approved,
            "approval_date": offer_letter.approval_date
        }, status=status.HTTP_200_OK)


class ApproveInternshipReportView(APIView):
    """Approve or reject an internship report using the student's university_id and report_id"""
    permission_classes = [IsAuthenticated]

    def put(self, request):
        university_id = request.data.get("university_id")
        report_id = request.data.get("report_id")  # Report identifier
        status_value = request.data.get("status")

        # Validate status
        if status_value not in ["Approved", "Rejected"]:
            return Response({"error": "Invalid status value"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the user
        user = request.user

        # Superusers can approve/reject any report
        if user.is_superuser:
            report = get_object_or_404(InternshipReport, id=report_id, student__university_id=university_id)
        else:
            advisor = getattr(user, "advisor", None)
            if not advisor:
                return Response({"error": "User is not an advisor"}, status=status.HTTP_403_FORBIDDEN)

            # Only fetch reports of the advisor's assigned students
            report = get_object_or_404(
                InternshipReport,
                id=report_id,
                student__university_id=university_id,
                student__assigned_advisor=advisor
            )

        # Convert "Approved"/"Rejected" to Boolean
        report.advisor_approved = status_value == "Approved"

        report.save()

        return Response({
            "message": f"Internship report {status_value.lower()} successfully",
            "student_name": report.student.full_name,  # Use full_name directly
            "student_university_id": university_id,
            "advisor_approved": report.advisor_approved
        }, status=status.HTTP_200_OK)