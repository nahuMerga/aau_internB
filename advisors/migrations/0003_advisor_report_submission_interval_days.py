# Generated by Django 5.2 on 2025-04-24 15:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('advisors', '0002_advisor_number_of_expected_reports'),
    ]

    operations = [
        migrations.AddField(
            model_name='advisor',
            name='report_submission_interval_days',
            field=models.PositiveIntegerField(default=15),
        ),
    ]
