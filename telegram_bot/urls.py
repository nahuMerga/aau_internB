from django.urls import path
from . import views

urlpatterns = [
    path('some-path/', views.some_view, name='some_view'),

]
