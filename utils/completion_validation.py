from django.utils import timezone
from student.models import Student

def check_internship_completion():
    """Automatically mark completed internships"""
    students = Student.objects.filter(status='Ongoing')
    
    for student in students:
        if timezone.now().date() > student.end_date:
            student.status = 'Completed'
            student.save()
            
            # Send completion notifications
            send_mail(
                'Internship Completed',
                'Congratulations! Your internship is now complete.',
                'system@univ.edu',
                [student.institutional_email]
            )