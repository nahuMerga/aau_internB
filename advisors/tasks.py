# advisors/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from advisors.models import Advisor
from internships.models import ThirdYearStudentList

@shared_task(bind=True, max_retries=3)
def notify_advisor_task(self, advisor_id):
    try:
        advisor = Advisor.objects.select_related('user').get(id=advisor_id)
        advisor_email = advisor.user.email

        students = ThirdYearStudentList.objects.filter(assigned_advisor=advisor)
        if not students.exists():
            return

        student_lines = [f"{s.full_name} (ID: {s.university_id})" for s in students]
        student_list_text = "\n".join(student_lines)

        subject = "AAU Internship – Your Assigned Students"
        message = (
            f"Dear {advisor.first_name},\n\n"
            f"You have been assigned the following students:\n\n"
            f"{student_list_text}\n\n"
            f"Best regards,\nAAU Internship Team"
        )
        
        send_mail(
            subject=subject,
            message=message,
            from_email="aau57.sis@gmail.com",
            recipient_list=[advisor_email],
            fail_silently=False,
        )
        return f"Notification sent to {advisor_email}"
    except Exception as e:
        self.retry(countdown=30, exc=e)
