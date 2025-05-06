from django.core.management.base import BaseCommand
from positions.models import Position, ScoreMatrix

class Command(BaseCommand):
    help = 'Создает матрицы пересчета баллов для специализаций, у которых их нет'

    def handle(self, *args, **options):
        positions = Position.objects.all()
        created_count = 0
        
        for position in positions:
            matrix, created = ScoreMatrix.objects.get_or_create(
                position=position,
                defaults={
                    'name': position.name,
                    'description': f'Матрица пересчета баллов для специализации {position.name}'
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Создана матрица для специализации "{position.name}"')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Создано {created_count} новых матриц')
        ) 