from django.urls import path
from .views import (
    StudentRegistrationView,
    InternshipOfferLetterUploadView,
    InternshipReportUploadView,
    OfferLetterStatusView,
    ReportStatusView
)

urlpatterns = [
    path("register/", StudentRegistrationView.as_view(), name="student-register"),
    path("upload-offer-letter/", InternshipOfferLetterUploadView.as_view(), name="upload-offer-letter"),
    path("upload-report/", InternshipReportUploadView.as_view(), name="upload-report"),
    path("offer-letter-status/", OfferLetterStatusView.as_view(), name="offer-letter-status"),
    path("report-status/", ReportStatusView.as_view(), name="report-status"),
]
