from internships.models import ThirdYearStudentList, InternshipPeriod
from advisors.models import Advisor
from django.utils import timezone
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
import datetime

scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")

from collections import defaultdict
from django.db.models import Count

def assign_advisors_to_third_year_students():
    """Assigns advisors to unassigned third-year students as fairly as possible"""
    students = ThirdYearStudentList.objects.filter(assigned_advisor__isnull=True).order_by("full_name")
    advisors = list(Advisor.objects.annotate(current_load=Count('thirdyearstudentlist')).order_by('current_load', 'first_name'))

    if not advisors:
        print("❌ No advisors available")
        return

    for student in students:
        # Always assign the advisor with the fewest students
        advisors[0].thirdyearstudentlist_set.add(student)
        student.assigned_advisor = advisors[0]
        student.save()

        # Update the current load by re-sorting the advisors list
        advisors = sorted(advisors, key=lambda a: a.thirdyearstudentlist_set.count())

    print(f"✅ Assigned advisors to {len(students)} students")


def check_and_assign():
    """Checks if registration period has ended and assigns advisors if needed"""
    try:
        period = InternshipPeriod.objects.latest("registration_end")
    except InternshipPeriod.DoesNotExist:
        print("⚠️ No internship period found")
        return

    if period.advisors_assigned:
        print("✅ Advisors already assigned. Stopping scheduler...")
        scheduler.remove_job('check_and_assign_job')
        scheduler.shutdown(wait=False)
        return

    # Create timezone-aware end datetime (3:35 PM on registration end date)
    end_datetime = timezone.make_aware(
        datetime.datetime.combine(
            period.registration_end,
            datetime.time(hour=15, minute=35)
        )
    )

    now = timezone.now()

    if now >= end_datetime:
        print("🟢 Registration period ended - assigning advisors")
        assign_advisors_to_third_year_students()
        
        # Mark assignment as complete
        period.advisors_assigned = True
        period.save()
        
        # Clean up scheduler
        scheduler.remove_job('check_and_assign_job')
        scheduler.shutdown(wait=False)
        print("🛑 Scheduler stopped after assignment")
    else:
        print(f"🔴 Registration ongoing (ends at {end_datetime})")

def start_scheduler():
    """Starts the background scheduler"""
    if not scheduler.running:
        try:
            scheduler.add_job(
                check_and_assign,
                'interval',
                minutes=1,
                id='check_and_assign_job',
                replace_existing=True
            )
            scheduler.start()
            print("⏰ Scheduler started - checking every minute")
        except Exception as e:
            print(f"❌ Failed to start scheduler: {e}")
