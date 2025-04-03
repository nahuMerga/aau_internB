def auto_assign_advisors():
    """Assign students to advisors alphabetically with even distribution"""
    with transaction.atomic():
        advisors = list(Advisor.objects.all().order_by('user__last_name'))
        students = Student.objects.filter(
            status='Pending'
        ).order_by('full_name')
        
        advisor_count = len(advisors)
        for index, student in enumerate(students):
            advisor = advisors[index % advisor_count]
            student.assigned_advisor = advisor
            student.save()
            advisor.assigned_students.add(student)