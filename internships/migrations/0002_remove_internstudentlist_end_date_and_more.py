# Generated by Django 5.1.7 on 2025-04-01 18:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('internships', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='internstudentlist',
            name='end_date',
        ),
        migrations.RemoveField(
            model_name='internstudentlist',
            name='phone_number',
        ),
        migrations.RemoveField(
            model_name='internstudentlist',
            name='start_date',
        ),
        migrations.RemoveField(
            model_name='internstudentlist',
            name='status',
        ),
        migrations.RemoveField(
            model_name='internstudentlist',
            name='telegram_id',
        ),
    ]
