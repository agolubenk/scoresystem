# Generated by Django 5.2 on 2025-05-06 10:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("positions", "0010_scorematrix_scorematrixcell_scorematrixsum"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="scorematrix",
            unique_together={("position", "name")},
        ),
    ]
