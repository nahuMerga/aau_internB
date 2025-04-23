from rest_framework import serializers
from .models import Department, Student, InternshipReport, InternshipOfferLetter
from advisors.models import Advisor

class AdvisorBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Advisor
        fields = ['id', 'first_name', 'last_name']

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'

class StudentSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)
    assigned_advisor = AdvisorBasicSerializer(read_only=True)
    
    class Meta:
        model = Student
        fields = '__all__'

class InternshipReportSerializer(serializers.ModelSerializer):
    telegram_id = serializers.CharField(write_only=True)
    document = serializers.FileField(write_only=True)

    class Meta:
        model = InternshipReport
        fields = ['telegram_id', 'report_number', 'document']

class InternshipOfferLetterSerializer(serializers.ModelSerializer):
    telegram_id = serializers.CharField(write_only=True)

    class Meta:
        model = InternshipOfferLetter
        fields = ['telegram_id', 'document']
        
# Serializer for reading internship reports
class InternshipReportReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternshipReport
        fields = [ 'report_number', 'document_url', 'submission_date', 'created_at']

# Serializer for reading offer letters
class InternshipOfferLetterReadSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = InternshipOfferLetter
        fields = [
            'company_name',
            'document_url',
            'advisor_approved',
            'approval_date',
            'submission_date',
            'created_at',
        ]
