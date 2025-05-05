from django.db import migrations

def migrate_position_data(apps, schema_editor):
    Position = apps.get_model('positions', 'Position')
    PositionGrade = apps.get_model('positions', 'PositionGrade')
    
    # Создаем записи в PositionGrade для каждой позиции
    for position in Position.objects.all():
        if hasattr(position, 'grade_id') and hasattr(position, 'confirmation_points') and hasattr(position, 'promotion_points'):
            PositionGrade.objects.create(
                position=position,
                grade_id=position.grade_id,
                confirmation_points=position.confirmation_points,
                promotion_points=position.promotion_points
            )

class Migration(migrations.Migration):

    dependencies = [
        ('positions', '0006_alter_position_options_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_position_data),
    ] 