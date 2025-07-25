# Generated by Django 4.2.21 on 2025-05-17 11:17

from django.db import migrations

def create_vacancies_and_profiles(apps, schema_editor):
    Position = apps.get_model('positions', 'Position')
    Vacancy = apps.get_model('positions', 'Vacancy')
    PositionProfile = apps.get_model('positions', 'PositionProfile')
    
    for position in Position.objects.all():
        # Проверяем, есть ли уже вакансия для этой специализации
        if not Vacancy.objects.filter(position=position).exists():
            # Создаем вакансию
            vacancy = Vacancy.objects.create(
                name=f'Вакансия {position.name}',
                position=position,
                description=f'Описание вакансии для специализации {position.name}'
            )
            
            # Создаем профиль должности
            PositionProfile.objects.create(
                vacancy=vacancy,
                profile_text=f'Профиль должности для специализации {position.name}'
            )

def reverse_vacancies_and_profiles(apps, schema_editor):
    PositionProfile = apps.get_model('positions', 'PositionProfile')
    Vacancy = apps.get_model('positions', 'Vacancy')
    
    # Удаляем все профили и вакансии
    PositionProfile.objects.all().delete()
    Vacancy.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('positions', '0025_vacancy_positionprofile'),
    ]

    operations = [
        migrations.RunPython(create_vacancies_and_profiles, reverse_vacancies_and_profiles),
    ]
