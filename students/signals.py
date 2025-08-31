# students/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Student, InternshipOfferLetter, InternshipReport

def clear_student_cache(student_id=None):
    """Clear student-related cache"""
    if student_id:
        cache.delete_pattern(f'student_{student_id}_*')
        cache.delete_pattern(f'telegram_{student_id}_*')
    cache.delete_pattern('student_*')
    cache.delete_pattern('offer_letter_*')
    cache.delete_pattern('internship_report_*')

@receiver([post_save, post_delete], sender=Student)
def invalidate_student_cache(sender, instance, **kwargs):
    """Clear cache when student data changes"""
    clear_student_cache(instance.id)
    if instance.telegram_id:
        cache.delete_pattern(f'telegram_{instance.telegram_id}_*')
    if instance.assigned_advisor:
        cache.delete_pattern(f'advisor_{instance.assigned_advisor.id}_*')

@receiver([post_save, post_delete], sender=InternshipOfferLetter)
def invalidate_offer_letter_cache(sender, instance, **kwargs):
    """Clear cache when offer letter changes"""
    clear_student_cache()
    if instance.student:
        clear_student_cache(instance.student.id)

@receiver([post_save, post_delete], sender=InternshipReport)
def invalidate_report_cache(sender, instance, **kwargs):
    """Clear cache when report changes"""
    clear_student_cache()
    if instance.student:
        clear_student_cache(instance.student.id)

