# Generated by Django 5.2 on 2025-04-22 23:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('internships', '0005_company_student'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='company',
            name='student',
        ),
    ]
