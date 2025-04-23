from rest_framework import serializers
from .models import Company, Internship, ThirdYearStudentList, InternStudentList, InternshipHistory
from students.serializers import DepartmentSerializer
from advisors.models import Advisor
from students.models import Student, InternshipOfferLetter

class AdvisorBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Advisor
        fields = ['id', 'first_name', 'last_name']

class CompanySerializer(serializers.ModelSerializer):
    telegram_id = serializers.CharField(write_only=True)  # Add telegram_id to serializer
    
    class Meta:
        model = Company
        fields = '__all__'

    def create(self, validated_data):
        telegram_id = validated_data.pop('telegram_id')  # Remove telegram_id from validated data

        # Find the student based on the telegram_id
        student = Student.objects.filter(telegram_id=telegram_id).first()
        if not student:
            raise serializers.ValidationError("Student not found.")

        # Create the company instance
        company = Company.objects.create(**validated_data)

        # Link the company to the student's internship offer letter
        InternshipOfferLetter.objects.create(
            student=student,
            company=company,  # Link the company here
            advisor_approved='Pending'  # Default value
        )

        return company

class ThirdYearStudentListSerializer(serializers.ModelSerializer):
    assigned_advisor = AdvisorBasicSerializer(read_only=True)
    
    class Meta:
        model = ThirdYearStudentList
        fields = '__all__'

class InternStudentListSerializer(serializers.ModelSerializer):
    student = ThirdYearStudentListSerializer(read_only=True)
    
    class Meta:
        model = InternStudentList
        fields = '__all__'

class InternshipSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)
    
    class Meta:
        model = Internship
        fields = '__all__'

class InternshipHistorySerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = InternshipHistory
        fields = ['id', 'student_name', 'company_name', 'year', 'start_date', 'end_date']