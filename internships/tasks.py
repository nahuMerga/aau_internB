# internships/tasks.py
from celery import shared_task
import pandas as pd
from django.db import transaction
from internships.models import ThirdYearStudentList
from advisors.models import Advisor
from advisors.tasks import notify_advisor_task
from utils.generate_email import generate_email
from utils.get_next_available_advisor import get_next_available_advisor

@shared_task(bind=True, max_retries=3)
def process_student_excel_task(self, file_path):
    """Process student Excel file asynchronously"""
    try:
        df = pd.read_excel(file_path)
        required_columns = {'university_id', 'full_name'}
        
        if not required_columns.issubset(df.columns):
            raise ValueError(f"Missing columns. Required: {required_columns}")

        created_students = []
        
        with transaction.atomic():
            for _, row in df.iterrows():
                university_id = str(row['university_id']).strip()[:20]
                full_name = str(row['full_name']).strip()

                if ThirdYearStudentList.objects.filter(university_id=university_id).exists():
                    continue

                email = generate_email(full_name, university_id)
                advisor = get_next_available_advisor()
                
                if not advisor:
                    raise ValueError("No available advisor.")

                student = ThirdYearStudentList.objects.create(
                    university_id=university_id,
                    full_name=full_name,
                    institutional_email=email,
                    assigned_advisor=advisor
                )

                created_students.append({
                    "university_id": university_id,
                    "full_name": full_name,
                    "email": email,
                    "advisor": advisor.first_name
                })

        # Notify all advisors about their new students
        for advisor in Advisor.objects.all():
            notify_advisor_task.delay(advisor.id)

        return {
            "message": f"{len(created_students)} students uploaded successfully.",
            "data": created_students
        }
    except Exception as e:
        self.retry(countdown=60, exc=e)
