from django.urls import path
from .views import SendOTPView

urlpatterns = [
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
]
