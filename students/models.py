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

class InternshipOfferLetter(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE)
    document = models.FileField(upload_to='offer_letters/')
    advisor_approved = models.BooleanField(default=False)
    submission_date = models.DateTimeField(auto_now_add=True)
    approval_date = models.DateTimeField(null=True, blank=True)

class InternshipReport(models.Model):
    REPORT_CHOICES = [(i, f"{i} Report") for i in range(1, 5)]

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    document = models.FileField(upload_to='reports/')
    submission_date = models.DateTimeField(auto_now_add=True)
    advisor_approved = models.BooleanField(default=False)
    approval_date = models.DateTimeField(null=True, blank=True)
    report_number = models.IntegerField(choices=REPORT_CHOICES)

    grade = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )

    class Meta:
        ordering = ['-submission_date']
        get_latest_by = 'submission_date'
        unique_together = ['student', 'report_number']  # Ensure no duplicate report numbers per student
