from django.contrib import admin

from .models import ThirdYearStudentList, InternStudentList,Department,  Company, Internship ,InternshipHistory

admin.site.register(ThirdYearStudentList)
admin.site.register(Company)
admin.site.register(InternStudentList)
admin.site.register(InternshipHistory)
admin.site.register(Internship)
admin.site.register(Department)
