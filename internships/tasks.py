from django.utils import timezone
from apscheduler.schedulers.background import BackgroundScheduler
from internships.models import InternshipPeriod
from .views import assign_students_to_advisors

def check_and_assign_advisors():
    """Runs daily to check if registration ended and assigns advisors"""
    today = timezone.now().date()
    latest_period = InternshipPeriod.objects.order_by("-registration_end").first()

    if latest_period and today > latest_period.registration_end:
        assign_students_to_advisors()

def start_scheduler():
    """Starts the scheduler to check daily"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_and_assign_advisors, "interval", days=1)  # Runs daily
    scheduler.start()
