from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from advisors.models import Advisor
from internships.models import Department, Company
from datetime import datetime

class Student(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Ongoing', 'Ongoing'),
        ('Completed', 'Completed')
    ]
    
    university_id = models.CharField(max_length=20, unique=True)
    institutional_email = models.EmailField(unique=True)
    otp_verified = models.BooleanField(default=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    telegram_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    internship_year = models.PositiveIntegerField(default=datetime.now().year, null=True, blank=True)
    assigned_advisor = models.ForeignKey(
        Advisor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.full_name} ({self.university_id})"

    def save(self, *args, **kwargs):
        if not self.assigned_advisor:
            try:
                # Lazy import to avoid circular import
                from internships.models import ThirdYearStudentList
                
                third_year_student = ThirdYearStudentList.objects.get(university_id=self.university_id)
                if third_year_student.assigned_advisor:
                    self.assigned_advisor = third_year_student.assigned_advisor  # Ensure this is an Advisor instance
                else:
                    print(f"⚠️ No advisor assigned for {third_year_student.full_name}")
            except ThirdYearStudentList.DoesNotExist:
                print(f"⚠️ No third-year student found with university_id {self.university_id}")
        
        # Ensure department is assigned properly (if it's not already assigned)
        if isinstance(self.department, str):
            self.department = Department.objects.get(name=self.department)  # Ensure this is a Department object or ID

        # Save the instance
        super(Student, self).save(*args, **kwargs)


class InternshipOfferLetter(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    submission_date = models.DateTimeField(auto_now_add=True)
    document = models.FileField(upload_to='offer_letters/', null=True, blank=True)
    document_url = models.URLField(blank=True, null=True)
    advisor_approved = models.CharField(
        max_length=10, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')],
        default='Pending'
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # ✅ Add this line
    
    def __str__(self):
        return f"Offer Letter for {self.student.full_name} at {self.company} - Status: {self.advisor_approved}"
    

class InternshipReport(models.Model):
    REPORT_CHOICES = [(i, f"{i} Report") for i in range(1, 5)]
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    document = models.FileField(upload_to='offer_letters/', null=True, blank=True)
    document_url = models.URLField(blank=True, null=True)
    submission_date = models.DateTimeField(auto_now_add=True)
    report_number = models.IntegerField(choices=REPORT_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)  # ✅ Add this line


    class Meta:
        ordering = ['-submission_date']
        get_latest_by = 'submission_date'
        unique_together = ['student', 'report_number']  # Ensure no duplicate report numbers per student
        
    def __str__(self):
        return f"Report {self.report_number} - {self.student.full_name}"

