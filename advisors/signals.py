from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Advisor
from students.models import Student, InternshipOfferLetter, InternshipReport
from internships.models import ThirdYearStudentList

def clear_advisor_cache(advisor_id):
    """Clear all cache related to a specific advisor"""
    # Clear advisor-specific cache patterns
    cache.delete_pattern(f'advisor_{advisor_id}_*')
    cache.delete_pattern(f'students_advisor_{advisor_id}_*')
    
    # Also clear general advisor cache
    cache.delete_pattern('advisor_students_*')
    cache.delete_pattern('advisor_profile_*')

@receiver([post_save, post_delete], sender=Advisor)
def invalidate_advisor_cache(sender, instance, **kwargs):
    """Clear cache when advisor data changes"""
    clear_advisor_cache(instance.id)
    # Also clear any user-specific cache
    if hasattr(instance, 'user'):
        cache.delete_pattern(f'user_{instance.user.id}_*')

@receiver([post_save, post_delete], sender=Student)
def invalidate_student_cache(sender, instance, **kwargs):
    """Clear cache when student data changes"""
    if instance.assigned_advisor:
        clear_advisor_cache(instance.assigned_advisor.id)
    # Clear student-specific cache
    cache.delete_pattern(f'student_{instance.university_id}_*')

@receiver([post_save, post_delete], sender=InternshipOfferLetter)
def invalidate_offer_letter_cache(sender, instance, **kwargs):
    """Clear cache when offer letter changes"""
    if instance.student and instance.student.assigned_advisor:
        clear_advisor_cache(instance.student.assigned_advisor.id)
    cache.delete_pattern('offer_letter_*')

@receiver([post_save, post_delete], sender=InternshipReport)
def invalidate_report_cache(sender, instance, **kwargs):
    """Clear cache when report changes"""
    if instance.student and instance.student.assigned_advisor:
        clear_advisor_cache(instance.student.assigned_advisor.id)
    cache.delete_pattern('internship_report_*')

@receiver([post_save, post_delete], sender=ThirdYearStudentList)
def invalidate_third_year_cache(sender, instance, **kwargs):
    """Clear cache when third year student list changes"""
    if instance.assigned_advisor:
        clear_advisor_cache(instance.assigned_advisor.id)
    cache.delete_pattern('third_year_students_*')
