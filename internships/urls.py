from django.urls import path
from .views import (
    AdminStudentsListView,
    AdminAdvisorsListView,
    AssignAdvisorView,
    InternshipPeriodView,
    AutoAssignAdvisorsView
)


urlpatterns = [
    path('students/', AdminStudentsListView.as_view(), name='admin-students-list'),
    path('advisors/', AdminAdvisorsListView.as_view(), name='admin-advisors-list'),
    path('assign-advisor/', AssignAdvisorView.as_view(), name='assign-advisor'),
    path('internship-period/', InternshipPeriodView.as_view(), name='internship-period'),
]
