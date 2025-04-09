from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from advisors.models import Advisor

class Student(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Ongoing', 'Ongoing'),
        ('Completed', 'Completed')
    ]
    
    university_id = models.CharField(max_length=20, unique=True)
    institutional_email = models.EmailField(unique=True)
    otp_verified = models.BooleanField(default=False)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    telegram_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    student_grade = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(40)]  # 4 reports × 10 points
    )
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
                # ⬇️ Lazy import to break circular dependency
                from internships.models import ThirdYearStudentList
                
                third_year_student = ThirdYearStudentList.objects.get(university_id=self.university_id)
                if third_year_student.assigned_advisor:
                    self.assigned_advisor = third_year_student.assigned_advisor
                else:
                    print(f"⚠️ No advisor assigned for {third_year_student.full_name}")
            except ThirdYearStudentList.DoesNotExist:
                print(f"⚠️ No third-year student found with university_id {self.university_id}")
        
        super(Student, self).save(*args, **kwargs)

class InternshipOfferLetter(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE)
    company = models.CharField(max_length=100)
    submission_date = models.DateTimeField(auto_now_add=True)
    document = models.FileField(upload_to='offer_letters/')
    document_url = models.URLField(blank=True, null=True)
    advisor_approved = models.CharField(
        max_length=10, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')],
        default='Pending'
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Offer Letter for {self.student.full_name} at {self.company} - Status: {self.advisor_approved}"


class InternshipReport(models.Model):
    REPORT_CHOICES = [(i, f"{i} Report") for i in range(1, 5)]
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    document = models.FileField(upload_to='offer_letters/')
    document_url = models.URLField(blank=True, null=True)
    submission_date = models.DateTimeField(auto_now_add=True)
    report_number = models.IntegerField(choices=REPORT_CHOICES)

    grade = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )

    class Meta:
        ordering = ['-submission_date']
        get_latest_by = 'submission_date'
        unique_together = ['student', 'report_number']  # Ensure no duplicate report numbers per student
        
    def __str__(self):
        return f"Report {self.report_number} - {self.student.full_name} | Grade: {self.grade}"

