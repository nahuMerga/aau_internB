# Generated by Django 5.1.7 on 2025-04-02 16:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('advisors', '0006_advisor_first_name_advisor_last_name_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='advisor',
            name='university_email',
        ),
    ]
