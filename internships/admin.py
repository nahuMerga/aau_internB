from django.contrib import admin
from .models import ThirdYearStudentList, InternStudentList, InternshipPeriod

admin.site.register(ThirdYearStudentList)

admin.site.register(InternStudentList)

admin.site.register(InternshipPeriod)
