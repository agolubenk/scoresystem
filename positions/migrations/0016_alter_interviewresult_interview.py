# Generated by Django 5.0.2 on 2025-05-06 12:52

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("positions", "0015_interview_general_notes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="interviewresult",
            name="interview",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="results",
                to="positions.interview",
                verbose_name="Интервью",
            ),
        ),
    ]
