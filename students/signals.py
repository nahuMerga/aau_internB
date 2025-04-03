from django.db.models.signals import post_save
from django.dispatch import receiver
from students.models import Student

@receiver(post_save, sender=Student)
def advisor_assignment_changed(sender, instance, **kwargs):
    """
    Triggered whenever a Student object is saved.
    If 'assigned_advisor' changes, perform an action.
    """
    if instance.assigned_advisor:  # Check if advisor was assigned
        print("Hello, World! Advisor status changed.")
