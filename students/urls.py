from django.urls import path
from .views import  InternshipOfferLetterUploadView, InternshipReportUploadView, StudentRegistrationView

urlpatterns = [
    path("register/", StudentRegistrationView.as_view(), name="student-register"),
    path('upload-offer-letter/', InternshipOfferLetterUploadView.as_view(), name='upload-offer-letter'),
    path('upload-report/', InternshipReportUploadView.as_view(), name='upload-report'),
]
