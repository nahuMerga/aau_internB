from django.urls import path
from .views import (
    AdminStudentsListView,
    AdminAdvisorsListView,
    AssignAdvisorView,
    AutoAssignAdvisorsView,
    CompanyListCreateView,
    InternshipHistoryListView,
    UploadStudentExcelView
)


urlpatterns = [
    path('students/', AdminStudentsListView.as_view(), name='admin-students-list'),
    path('companies/', CompanyListCreateView.as_view(), name='company-list-create'),
    path('advisors/', AdminAdvisorsListView.as_view(), name='admin-advisors-list'),
    path('assign-advisor/', AssignAdvisorView.as_view(), name='assign-advisor'),
    path('upload-students/', UploadStudentExcelView.as_view(), name='upload-students'),
    path('internship-history/', InternshipHistoryListView.as_view(), name='internship-history-list'),
]
