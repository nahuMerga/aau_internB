from advisors.models import Advisor
from django.db.models import Count

def get_next_available_advisor():
    advisors = Advisor.objects.annotate(
        student_count=Count('thirdyearstudentlist')
    ).order_by('student_count', 'first_name')
    return advisors.first() if advisors.exists() else None
