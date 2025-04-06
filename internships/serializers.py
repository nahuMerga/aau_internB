from rest_framework import serializers
from .models import InternStudentList, InternshipPeriod, ThirdYearStudentList

class ThirdYearStudentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThirdYearStudentList
        fields = ['university_id', 'full_name', 'institutional_email', 'assigned_advisor'] 

class InternStudentListSerializer(serializers.ModelSerializer):
    student = ThirdYearStudentListSerializer()  # Nested serializer for the student
    class Meta:
        model = InternStudentList
        fields = ['student', 'phone_number', 'telegram_id', 'status', 'start_date', 'end_date']

class InternshipPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternshipPeriod
        fields = ['registration_start', 'registration_end', 'internship_start', 'internship_end']
