# Generated by Django 5.2 on 2025-04-22 23:31

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('internships', '0006_remove_company_student'),
        ('students', '0003_alter_internshipofferletter_company'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='internships.company'),
        ),
    ]
