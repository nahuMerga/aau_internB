from django.db import models
from students.models import Student
from advisors.models import Advisor

class ThirdYearStudentList(models.Model):
    university_id = models.CharField(max_length=20, unique=True, primary_key=True)
    full_name = models.CharField(max_length=100)
    institutional_email = models.EmailField(unique=True)
    assigned_advisor = models.ForeignKey(Advisor, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        advisor_name = self.assigned_advisor.first_name if self.assigned_advisor else "No Advisor"
        return f"{self.full_name} ({self.university_id}) - Advisor: {advisor_name}"



class InternStudentList(models.Model):
    student = models.OneToOneField(
        ThirdYearStudentList,
        on_delete=models.CASCADE,
        related_name='internship_record'
    )
    # phone_number = models.CharField(max_length=15)
    # telegram_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    # status = models.CharField(
    #     max_length=10,
    #     choices=[('Pending', 'Pending'), ('Ongoing', 'Ongoing'), ('Completed', 'Completed')],
    #     default='Pending'
    # )
    # start_date = models.DateField(null=True, blank=True)
    # end_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.student.full_name}'s Internship"  # Customize as needed

class InternshipPeriod(models.Model):
    registration_start = models.DateField()
    registration_end = models.DateField()
    internship_start = models.DateField()
    internship_end = models.DateField()
    advisors_assigned = models.BooleanField(default=False) 
    
    def is_registration_active(self):
        from django.utils import timezone
        now = timezone.now().date()
        return self.registration_start <= now <= self.registration_end
    
    def is_valid_calendar(self):
        """Check if internship start and end dates are valid (start before end)."""
        if self.internship_start > self.internship_end:
            return False
        return True
    
    def __str__(self):
        return f"Registration: {self.registration_start} to {self.registration_end}"
