from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (AdvisorRegistrationView, 
                    LoginView, LogoutView,
                    AdvisorStudentsView,
                    ApproveOfferLetterView, UpdateAdvisorProfileView, StudentDetailView, UpdateAdvisorSettingsView
                    )



urlpatterns = [
    path('students/', AdvisorStudentsView.as_view(), name='advisor-students'),
    path("students/<str:university_id>/", StudentDetailView.as_view(), name="student-detail"),
    path('profile/', UpdateAdvisorProfileView.as_view(), name='update-advisor-profile'),
    path("update-settings/", UpdateAdvisorSettingsView.as_view(), name="update-advisor-settings"),
    path('approve-offer-letter/', ApproveOfferLetterView.as_view(), name='approve-offer-letter'),
    path('register/', AdvisorRegistrationView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
