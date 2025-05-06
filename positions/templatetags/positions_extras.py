from django import template
from django.db.models import Sum
from ..models import PositionGrade

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Получить значение из словаря по ключу или кортежу ключей"""
    if isinstance(key, str) and ',' in key:
        # Если ключи переданы как строка с разделителем
        key = tuple(int(k.strip()) for k in key.split(','))
    return dictionary.get(key) if isinstance(key, tuple) else dictionary.get(key)

@register.filter
def sum_scores(results):
    return sum(float(result.score) for result in results)

@register.filter
def get_recommended_grade(results):
    if not results:
        return None
        
    interview = results[0].interview
    total_score = sum(float(result.score) for result in results)
    
    # Получаем все грейды для позиции, отсортированные по убыванию
    position_grades = PositionGrade.objects.filter(
        position=interview.position
    ).select_related('grade').order_by('-grade__order')
    
    # Ищем первый грейд, для которого набранных баллов достаточно
    for position_grade in position_grades:
        if total_score >= position_grade.confirmation_points:
            return position_grade.grade.name
            
    return None 