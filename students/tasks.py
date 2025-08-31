# students/tasks.py
from celery import shared_task
from django.core.mail import send_mail
import requests
from django.core.exceptions import ValidationError

@shared_task(bind=True, max_retries=3)
def send_registration_email_task(self, student_name, student_email, advisor_data):
    try:
        message = (
            f"Dear {student_name},\n\n"
            f"You have successfully registered for the internship program!\n\n"
            f"Your advisor information:\n"
            f"Name: {advisor_data.get('name', 'Not assigned')}\n"
            f"Email: {advisor_data.get('email', 'Not available')}\n"
            f"Phone: {advisor_data.get('phone', 'Not available')}\n\n"
            f"Best regards,\nAAU Internship Team"
        )
        
        send_mail(
            subject="AAU Internship Registration Confirmation",
            message=message,
            from_email="aau57.sis@gmail.com",
            recipient_list=[student_email],
            fail_silently=False,
        )
        return f"Registration confirmation sent to {student_email}"
    except Exception as e:
        self.retry(countdown=30, exc=e)
        

@shared_task(bind=True, max_retries=3)
def upload_to_supabase_task(self, file_content, path_in_bucket, content_type):
    """Upload file to Supabase storage"""
    SUPABASE_URL = "https://cavdgitwbubdtqdctvlz.supabase.co"
    SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNhdmRnaXR3YnViZHRxZGN0dmx6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQxOTUyMTQsImV4cCI6MjA1OTc3MTIxNH0.Xs8TmxZbub6C4WK8qwCiZ0pPfbXbPLDIyandKuyUtgY"
    SUPABASE_BUCKET = "student-document"

    upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{path_in_bucket}"
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": content_type,
        "x-upsert": "true"
    }

    try:
        response = requests.put(upload_url, headers=headers, data=file_content)
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Upload failed: {response.status_code} - {response.text}")

        return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{path_in_bucket}"
    except Exception as e:
        self.retry(countdown=30, exc=e)
