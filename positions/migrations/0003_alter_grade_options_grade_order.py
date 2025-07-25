# Generated by Django 5.2 on 2025-05-05 15:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("positions", "0002_alter_position_options_remove_grade_description_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="grade",
            options={
                "ordering": ["order"],
                "verbose_name": "Грейд",
                "verbose_name_plural": "Грейды",
            },
        ),
        migrations.AddField(
            model_name="grade",
            name="order",
            field=models.IntegerField(default=0, verbose_name="Порядок"),
        ),
    ]
