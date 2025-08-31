# internships/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Company, ThirdYearStudentList, InternshipHistory

def clear_internship_cache():
    """Clear all internship-related cache"""
    cache.delete_pattern('internship_*')
    cache.delete_pattern('company_*')
    cache.delete_pattern('admin_students_*')
    cache.delete_pattern('admin_advisors_*')

@receiver([post_save, post_delete], sender=Company)
def invalidate_company_cache(sender, instance, **kwargs):
    """Clear cache when company data changes"""
    clear_internship_cache()
    cache.delete_pattern(f'company_{instance.id}_*')
    cache.delete_pattern(f'company_telegram_{instance.telegram_id}_*')

@receiver([post_save, post_delete], sender=ThirdYearStudentList)
def invalidate_third_year_cache(sender, instance, **kwargs):
    """Clear cache when third year student data changes"""
    clear_internship_cache()
    cache.delete_pattern('third_year_students_*')
    if instance.assigned_advisor:
        cache.delete_pattern(f'advisor_{instance.assigned_advisor.id}_*')

@receiver([post_save, post_delete], sender=InternshipHistory)
def invalidate_internship_history_cache(sender, instance, **kwargs):
    """Clear cache when internship history changes"""
    clear_internship_cache()
    cache.delete_pattern('internship_history_*')
    cache.delete_pattern(f'internship_history_year_{instance.year}_*')
