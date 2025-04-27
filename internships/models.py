from django.db import models
# from students.models import Student
from advisors.models import Advisor
from django.apps import apps
from datetime import datetime
# from students.models import Student

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    internship_duration_weeks = models.PositiveIntegerField()
    internship_start = models.DateField()
    internship_end = models.DateField()
    

    def is_valid_calendar(self):
        """Check if internship dates are valid"""
        return self.internship_start <= self.internship_end

    def __str__(self):
        return self.name


class Company(models.Model):
    telegram_id = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    supervisor_name = models.CharField(max_length=100)
    supervisor_email = models.EmailField(null=True, blank=True)
    supervisor_phone = models.CharField(max_length=20, null=True, blank=True)
    position = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)



    def __str__(self):
        return self.name

class Internship(models.Model):
    student = models.ForeignKey(
        'students.Student',  # use string reference
        on_delete=models.CASCADE
    )
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=15, choices=[('Ongoing', 'Ongoing'), ('Completed', 'Completed')], default='Ongoing')

    def __str__(self):
        return f"{self.student.full_name} - {self.company.name}"

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

    
    def __str__(self):
        return f"{self.student.full_name}'s Internship"  # Customize as needed


class InternshipHistory(models.Model):
    student = models.ForeignKey(
        'students.Student',  # use string reference
        on_delete=models.CASCADE
    )
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True)
    year = models.PositiveIntegerField(default=datetime.now().year)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.student.full_name} - {self.year}"

