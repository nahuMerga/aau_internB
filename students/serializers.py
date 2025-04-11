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
    document = serializers.FileField(write_only=True)  # For file upload
    
    class Meta:
        model = InternshipOfferLetter
        fields = ['telegram_id', 'company', 'document', 'document_url']
        extra_kwargs = {
            'document': {'required': False, 'allow_null': True}  # Making the document field nullable
        }

    def create(self, validated_data):
        return super().create(validated_data)

class InternshipReportSerializer(serializers.ModelSerializer):
    document = serializers.FileField(write_only=True, use_url=False)
    telegram_id = serializers.CharField(write_only=True)
    
    class Meta:
        model = InternshipReport
        fields = ['telegram_id', 'report_number', 'document', 'document_url']
        extra_kwargs = {
            'document': {'required': False, 'allow_null': True}  # Making the document field nullable
        }

    def create(self, validated_data):
        return super().create(validated_data)
