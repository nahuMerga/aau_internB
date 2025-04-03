from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Count
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from apscheduler.schedulers.background import BackgroundScheduler
from internships.models import InternshipPeriod
from students.models import Student
from advisors.models import Advisor
from students.serializers import StudentSerializer, InternshipOfferLetterSerializer,InternshipReportSerializer
from advisors.serializers import AdvisorSerializer
from internships.serializers import InternshipPeriodSerializer

class AdminStudentsListView(generics.ListAPIView):
    """Admin can view all students"""
    serializer_class = StudentSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Student.objects.all()

class AdminAdvisorsListView(generics.ListAPIView):
    """Admin can view all advisors"""
    serializer_class = AdvisorSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Advisor.objects.all()


class AssignAdvisorView(APIView):
    """Admin assigns students to advisors manually using student university_id and advisor username"""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        university_id = request.data.get("university_id")  # Use university_id instead of student_id
        advisor_username = request.data.get("advisor_username")  # Use username instead of ID

        student = get_object_or_404(Student, university_id=university_id)  # Fetch student by university_id
        advisor = get_object_or_404(Advisor, user__username=advisor_username)  # Fetch advisor by username

        student.assigned_advisor = advisor
        student.save()

        return Response({"message": "Student assigned to advisor successfully"}, status=status.HTTP_200_OK)
    

class AutoAssignAdvisorsView(APIView):
    """Triggers auto assignment manually from frontend"""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        assign_students_to_advisors()
        return Response({"message": "Automatic advisor assignment triggered"}, status=status.HTTP_200_OK)

def assign_students_to_advisors():
    """Sort students alphabetically and distribute them evenly among advisors"""
    students = Student.objects.filter(assigned_advisor__isnull=True).order_by("full_name")
    advisors = list(Advisor.objects.all().order_by("first_name"))

    if not advisors:
        print("No advisors available")
        return

    advisor_index = 0
    advisor_count = len(advisors)

    for student in students:
        assigned_advisor = advisors[advisor_index]
        student.assigned_advisor = assigned_advisor
        student.save()
        advisor_index = (advisor_index + 1) % advisor_count  # Distribute evenly

    print("Auto assignment completed")


class InternshipPeriodView(APIView):
    """Get or update internship periods"""
    
    def get(self, request):
        try:
            period = InternshipPeriod.objects.latest('registration_start')  # Get the most recent period
            serializer = InternshipPeriodSerializer(period)
            return Response(serializer.data)
        except InternshipPeriod.DoesNotExist:
            return Response({"error": "No internship period found"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request):
        """Update the latest internship period (only admins allowed)"""
        try:
            period = InternshipPeriod.objects.latest('registration_start')
        except InternshipPeriod.DoesNotExist:
            return Response({"error": "No internship period found to update."}, status=status.HTTP_404_NOT_FOUND)

        serializer = InternshipPeriodSerializer(period, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

