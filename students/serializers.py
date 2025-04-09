from rest_framework import serializers
from students.models import Student, InternshipOfferLetter, InternshipReport
from internships.models import InternStudentList

class StudentSerializer(serializers.ModelSerializer):
    assigned_advisor = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "university_id",
            "institutional_email",
            "full_name",
            "phone_number",
            "telegram_id",
            "status",
            "start_date",
            "end_date",
            "student_grade",
            "assigned_advisor",
        ]

    def get_assigned_advisor(self, obj):
        return obj.assigned_advisor.full_name if obj.assigned_advisor else "Pending (Not assigned yet)"


class InternStudentSerializer(serializers.ModelSerializer):
    student = serializers.SerializerMethodField()

    class Meta:
        model = InternStudentList
        fields = [
            "student",
            "phone_number",
            "telegram_id",
            "status",
            "start_date",
            "end_date",
        ]

    def get_student(self, obj):
        return obj.student.full_name if obj.student else None


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'
        read_only_fields = ['assigned_advisor', 'otp_verified']  # Prevent students from modifying this field

class InternshipOfferLetterSerializer(serializers.ModelSerializer):
    telegram_id = serializers.CharField(write_only=True)
    document = serializers.FileField(write_only=True)  # Keep this for file upload
    
    # Add document_url as a read-only field if it’s supposed to provide the URL
    document_url = serializers.SerializerMethodField()

    class Meta:
        model = InternshipOfferLetter
        fields = ['telegram_id', 'company', 'document', 'document_url']
        extra_kwargs = {'document': {'required': True}}

    # Method to get the URL of the uploaded document
    def get_document_url(self, obj):
        return obj.document.url if obj.document else None

    def create(self, validated_data):
        # We don't need to pop the document field if we're not manually handling file saving
        return super().create(validated_data)

class InternshipReportSerializer(serializers.ModelSerializer):
    document = serializers.FileField(write_only=True, use_url=False)  # Don't include the URL in the response
    telegram_id = serializers.CharField(write_only=True)
    
    # Add document_url as a read-only field if it’s supposed to provide the URL
    document_url = serializers.SerializerMethodField()

    class Meta:
        model = InternshipReport
        fields = ['telegram_id', 'report_number', 'document', 'document_url']
        extra_kwargs = {'document': {'required': True}}

    # Method to get the URL of the uploaded document
    def get_document_url(self, obj):
        # Ensure 'document' is a valid field before trying to access its URL
        if hasattr(obj, 'document') and obj.document:
            return obj.document.url
        return None

    def create(self, validated_data):
        return super().create(validated_data)

