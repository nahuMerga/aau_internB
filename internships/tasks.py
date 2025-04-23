# from internships.models import ThirdYearStudentList
# from advisors.models import Advisor
# from students.models import Department
# from django.utils import timezone
# from apscheduler.schedulers.background import BackgroundScheduler
# from django_apscheduler.jobstores import DjangoJobStore
# import datetime
# from collections import defaultdict
# from django.db.models import Count

# scheduler = BackgroundScheduler()
# scheduler.add_jobstore(DjangoJobStore(), "default")

# def assign_advisors_to_third_year_students():
#     """Assigns advisors to unassigned third-year students as fairly as possible"""
#     students = ThirdYearStudentList.objects.filter(assigned_advisor__isnull=True).order_by("full_name")
#     advisors = list(Advisor.objects.annotate(current_load=Count('thirdyearstudentlist')).order_by('current_load', 'first_name'))

#     if not advisors:
#         print("❌ No advisors available")
#         return

#     for student in students:
#         # Always assign the advisor with the fewest students
#         advisors[0].thirdyearstudentlist_set.add(student)
#         student.assigned_advisor = advisors[0]
#         student.save()

#         # Update the current load by re-sorting the advisors list
#         advisors = sorted(advisors, key=lambda a: a.thirdyearstudentlist_set.count())

#     print(f"✅ Assigned advisors to {len(students)} students")

# def check_and_assign():
#     """Checks if registration period has ended in any department and assigns advisors if needed"""
#     try:
#         # Get all departments where registration has ended but advisors haven't been assigned
#         departments = Department.objects.filter(
#             registration_end__lte=timezone.now().date(),
#             advisors_assigned=False
#         )
#     except Exception as e:
#         print(f"⚠️ Error fetching departments: {e}")
#         return

#     if not departments.exists():
#         print("🔴 No departments with completed registration periods needing advisor assignment")
#         return

#     for department in departments:
#         print(f"🟢 Registration period ended for {department.name} - assigning advisors")
        
#         # Assign advisors to students in this department
#         assign_advisors_to_third_year_students()
        
#         # Mark assignment as complete for this department
#         department.advisors_assigned = True
#         department.save()
    
#     # Check if we should stop the scheduler (when all departments are processed)
#     remaining_departments = Department.objects.filter(
#         registration_end__lte=timezone.now().date(),
#         advisors_assigned=False
#     ).exists()
    
#     if not remaining_departments:
#         print("✅ All departments processed. Stopping scheduler...")
#         scheduler.remove_job('check_and_assign_job')
#         scheduler.shutdown(wait=False)

# def start_scheduler():
#     """Starts the background scheduler"""
#     if not scheduler.running:
#         try:
#             scheduler.add_job(
#                 check_and_assign,
#                 'interval',
#                 minutes=1,
#                 id='check_and_assign_job',
#                 replace_existing=True
#             )
#             scheduler.start()
#             print("⏰ Scheduler started - checking every minute")
#         except Exception as e:
#             print(f"❌ Failed to start scheduler: {e}")