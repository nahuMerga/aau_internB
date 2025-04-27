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
    class Meta:
        model = Company
        fields = '__all__'
        extra_kwargs = {
            'address': {'required': False, 'allow_blank': True},
            'supervisor_email': {'required': False, 'allow_blank': True},
            'supervisor_phone': {'required': False, 'allow_blank': True},
            'description': {'required': False, 'allow_blank': True},
        }

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