from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, ListView
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
import json
from django.core.serializers import serialize
from .models import Grade, Position, Parameter, ParameterDescription, PositionGrade, InterviewQuestion
from .forms import GradeForm
from django.contrib.auth.decorators import login_required

class GradeListView(ListView):
    model = Grade
    template_name = 'positions/grades.html'
    context_object_name = 'grades'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_order'] = Grade.objects.count() + 1
        return context

    def get(self, request, *args, **kwargs):
        if 'pk' in kwargs:
            grade = get_object_or_404(Grade, pk=kwargs['pk'])
            return JsonResponse({
                'success': True,
                'grade': {
                    'id': grade.id,
                    'name': grade.name,
                    'positions': grade.positions,
                    'order': grade.order
                }
            })
        return super().get(request, *args, **kwargs)

    def post(self, request):
        try:
            data = json.loads(request.body)
            form = GradeForm(data)
            if form.is_valid():
                grade = form.save()
                return JsonResponse({
                    'success': True,
                    'grade': {
                        'id': grade.id,
                        'name': grade.name,
                        'positions': grade.positions,
                        'order': grade.order
                    }
                })
            return JsonResponse({'success': False, 'errors': form.errors})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'errors': {'form': 'Invalid JSON data'}})

    def put(self, request, pk):
        try:
            data = json.loads(request.body)
            grade = get_object_or_404(Grade, pk=pk)
            form = GradeForm(data, instance=grade)
            if form.is_valid():
                grade = form.save()
                return JsonResponse({
                    'success': True,
                    'grade': {
                        'id': grade.id,
                        'name': grade.name,
                        'positions': grade.positions,
                        'order': grade.order
                    }
                })
            return JsonResponse({'success': False, 'errors': form.errors})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'errors': {'form': 'Invalid JSON data'}})

class GradeCreateView(CreateView):
    model = Grade
    form_class = GradeForm
    template_name = 'positions/grade_form.html'
    success_url = '/grades/'

def positions_list(request):
    grades = Grade.objects.all().order_by('order')
    positions = Position.objects.all().order_by('name')
    
    # Получаем все связи позиций с грейдами с оптимизацией запросов
    position_grades = PositionGrade.objects.select_related('position', 'grade').all()
    
    # Создаем словарь для хранения позиций по грейдам
    positions_by_grade = {}
    for grade in grades:
        positions_by_grade[grade.id] = position_grades.filter(grade=grade)
    
    # Получаем список уникальных специализаций
    unique_positions = positions.values_list('name', flat=True)
    
    # Преобразуем грейды в JSON
    grades_data = []
    for grade in grades:
        grades_data.append({
            'pk': grade.id,
            'fields': {
                'name': grade.name,
                'order': grade.order
            }
        })
    grades_json = json.dumps(grades_data)
    
    return render(request, 'positions/positions.html', {
        'grades': grades,
        'positions_by_grade': positions_by_grade,
        'unique_positions': unique_positions,
        'grades_json': grades_json
    })

@require_http_methods(["POST"])
def create_position(request):
    try:
        data = json.loads(request.body)
        
        # Проверяем наличие необходимых полей
        required_fields = ['name', 'grade_id', 'confirmation_points', 'promotion_points']
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    'success': False,
                    'errors': {field: 'Это поле обязательно для заполнения'}
                })
        
        # Создаем или получаем существующую позицию
        position, created = Position.objects.get_or_create(
            name=data['name']
        )
        
        # Создаем связь позиции с грейдом
        position_grade, created = PositionGrade.objects.get_or_create(
            position=position,
            grade_id=data['grade_id'],
            defaults={
                'confirmation_points': data['confirmation_points'],
                'promotion_points': data['promotion_points']
            }
        )
        
        # Если связь уже существует, обновляем баллы
        if not created:
            position_grade.confirmation_points = data['confirmation_points']
            position_grade.promotion_points = data['promotion_points']
            position_grade.save()
        
        return JsonResponse({
            'success': True,
            'position': {
                'id': position.id,
                'name': position.name,
                'grade_id': position_grade.grade_id,
                'confirmation_points': position_grade.confirmation_points,
                'promotion_points': position_grade.promotion_points
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'errors': {'form': 'Неверный формат данных'}})
    except Exception as e:
        return JsonResponse({'success': False, 'errors': {'form': str(e)}})

@require_http_methods(["POST"])
def update_position_by_id(request, pk):
    try:
        data = json.loads(request.body)
        position_name = data.get('position_name')
        grade_id = pk
        
        if not position_name:
            return JsonResponse({'success': False, 'errors': {'position_name': 'Не указано название специализации'}}, status=400)
            
        position = get_object_or_404(Position, name=position_name)
        
        # Получаем или создаем связь позиции с грейдом
        position_grade, created = PositionGrade.objects.get_or_create(
            position=position,
            grade_id=grade_id,
            defaults={
                'confirmation_points': 0,
                'promotion_points': 0
            }
        )
        
        if 'confirmation_points' in data:
            position_grade.confirmation_points = data['confirmation_points']
        if 'promotion_points' in data:
            position_grade.promotion_points = data['promotion_points']
            
        position_grade.save()
        
        return JsonResponse({
            'success': True,
            'position': {
                'id': position.id,
                'name': position.name,
                'grade_id': position_grade.grade_id,
                'confirmation_points': position_grade.confirmation_points,
                'promotion_points': position_grade.promotion_points
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'errors': {'form': 'Неверный формат данных'}}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'errors': {'form': str(e)}}, status=500)

@require_http_methods(["POST"])
def update_position_by_name(request):
    try:
        data = json.loads(request.body)
        old_name = data.get('old_name')
        new_name = data.get('new_name')

        if not old_name or not new_name:
            return JsonResponse({'success': False, 'errors': ['Не указано старое или новое название специализации']}, content_type='application/json')

        # Находим все позиции с таким названием
        positions = Position.objects.filter(name=old_name)
        if not positions.exists():
            return JsonResponse({'success': False, 'errors': ['Специализация не найдена']}, content_type='application/json')

        # Обновляем все найденные позиции
        positions.update(name=new_name)

        return JsonResponse({'success': True}, content_type='application/json')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'errors': ['Неверный формат данных']}, content_type='application/json')
    except Exception as e:
        return JsonResponse({'success': False, 'errors': [str(e)]}, content_type='application/json')

@require_http_methods(["DELETE"])
def delete_position(request, position_name):
    try:
        positions = Position.objects.filter(name=position_name)
        if positions.exists():
            positions.delete()
            return JsonResponse({'success': True}, content_type='application/json')
        return JsonResponse({'success': False, 'errors': {'position': 'Position not found'}}, content_type='application/json')
    except Exception as e:
        return JsonResponse({'success': False, 'errors': {'form': str(e)}}, content_type='application/json')

@login_required
def parameters(request):
    grades = Grade.objects.all()
    position_name = request.GET.get('position', '')
    
    # Получаем параметры с учетом фильтра по специализации
    if position_name:
        parameters = Parameter.objects.filter(position__name=position_name)
    else:
        parameters = Parameter.objects.all()
    
    # Получаем список всех специализаций
    positions = Position.objects.values('name').distinct()
    
    # Получаем описания параметров с учетом фильтра
    parameters_by_grade = {}
    for grade in grades:
        if position_name:
            # Фильтруем описания только для выбранной специализации
            parameters_by_grade[grade.id] = ParameterDescription.objects.filter(
                grade=grade,
                parameter__position__name=position_name
            )
        else:
            # Получаем все описания
            parameters_by_grade[grade.id] = ParameterDescription.objects.filter(grade=grade)
    
    context = {
        'grades': grades,
        'parameters': parameters,
        'positions': positions,
        'parameters_by_grade': parameters_by_grade,
        'grades_json': json.dumps(list(grades.values('pk', 'name')))
    }
    return render(request, 'positions/parameters.html', context)

@login_required
@require_http_methods(['POST'])
def create_parameter(request):
    try:
        data = json.loads(request.body)
        position_name = request.GET.get('position', '')
        
        # Создаем параметр
        parameter = Parameter.objects.create(
            name=data['name'],
            position=Position.objects.get(name=position_name) if position_name else None
        )
        
        return JsonResponse({
            'success': True, 
            'parameter_id': parameter.id,
            'parameter_name': parameter.name
        })
    except Exception as e:
        return JsonResponse({'success': False, 'errors': str(e)})

@login_required
@require_http_methods(['POST'])
def update_parameter(request, parameter_id):
    try:
        data = json.loads(request.body)
        parameter = Parameter.objects.get(id=parameter_id)
        parameter.name = data['name']
        parameter.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'errors': str(e)})

@login_required
@require_http_methods(['DELETE'])
def delete_parameter(request, parameter_id):
    try:
        parameter = Parameter.objects.get(id=parameter_id)
        parameter.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'errors': str(e)})

@login_required
@require_http_methods(['POST'])
def create_parameter_description(request):
    try:
        data = json.loads(request.body)
        position_name = request.GET.get('position', '')
        
        # Проверяем наличие всех необходимых полей
        if not all(key in data for key in ['parameter_id', 'grade_id', 'description']):
            return JsonResponse({'success': False, 'errors': 'Отсутствуют обязательные поля'})
        
        # Получаем объекты
        parameter = get_object_or_404(Parameter, id=data['parameter_id'])
        grade = get_object_or_404(Grade, id=data['grade_id'])
        
        # Если указана специализация, проверяем соответствие
        if position_name and parameter.position and parameter.position.name != position_name:
            return JsonResponse({'success': False, 'errors': 'Параметр не принадлежит выбранной специализации'})
        
        # Создаем описание
        description = ParameterDescription.objects.create(
            parameter=parameter,
            grade=grade,
            description=data['description']
        )
        
        return JsonResponse({
            'success': True,
            'description_id': description.id,
            'description': description.description
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'errors': 'Неверный формат данных'})
    except Exception as e:
        return JsonResponse({'success': False, 'errors': str(e)})

@login_required
@require_http_methods(['POST'])
def update_parameter_description(request, description_id):
    try:
        data = json.loads(request.body)
        description = ParameterDescription.objects.get(id=description_id)
        description.description = data['description']
        description.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'errors': str(e)})

@login_required
@require_http_methods(['DELETE'])
def delete_parameter_description(request, description_id):
    try:
        description = ParameterDescription.objects.get(id=description_id)
        description.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'errors': str(e)})

@login_required
def questions_list(request):
    positions = Position.objects.all()
    position_name = request.GET.get('position', '')
    
    # Получаем вопросы с учетом фильтра по специализации
    if position_name:
        questions = InterviewQuestion.objects.filter(position__name=position_name)
    else:
        questions = InterviewQuestion.objects.all()
    
    # Получаем типы вопросов из модели
    question_types = InterviewQuestion.QUESTION_TYPES
    test_types = InterviewQuestion.TEST_TYPES
    
    context = {
        'positions': positions,
        'questions': questions,
        'selected_position': position_name,
        'question_types': question_types,
        'test_types': test_types
    }
    
    return render(request, 'positions/questions.html', context)

@require_http_methods(["POST"])
def create_question(request):
    try:
        data = json.loads(request.body)
        position_name = request.GET.get('position', '')
        
        # Проверяем обязательные поля
        if not data.get('text'):
            return JsonResponse({'success': False, 'errors': {'text': 'Не указан текст вопроса'}}, status=400)
        if not data.get('question_type'):
            return JsonResponse({'success': False, 'errors': {'question_type': 'Не указан тип вопроса'}}, status=400)
            
        # Если тип вопроса "тестовое", проверяем наличие типа тестового
        if data['question_type'] == 'test' and not data.get('test_type'):
            return JsonResponse({'success': False, 'errors': {'test_type': 'Не указан тип тестового задания'}}, status=400)
        
        # Получаем или создаем позицию
        if position_name:
            position = get_object_or_404(Position, name=position_name)
        else:
            return JsonResponse({'success': False, 'errors': {'position': 'Не указана специализация'}}, status=400)
        
        # Создаем вопрос
        question = InterviewQuestion.objects.create(
            text=data['text'],
            position=position,
            question_type=data['question_type'],
            test_type=data.get('test_type'),
            order=InterviewQuestion.objects.filter(position=position).count() + 1
        )
        
        return JsonResponse({
            'success': True,
            'question': {
                'id': question.id,
                'text': question.text,
                'question_type': question.question_type,
                'test_type': question.test_type,
                'order': question.order
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'errors': {'form': 'Неверный формат данных'}}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'errors': {'form': str(e)}}, status=500)

@require_http_methods(["POST"])
def update_question(request, question_id):
    try:
        data = json.loads(request.body)
        question = get_object_or_404(InterviewQuestion, id=question_id)
        
        # Обновляем поля
        if 'text' in data:
            question.text = data['text']
        if 'question_type' in data:
            question.question_type = data['question_type']
            # Если тип изменился на не тестовый, очищаем тип тестового
            if data['question_type'] != 'test':
                question.test_type = None
        if 'test_type' in data and data['question_type'] == 'test':
            question.test_type = data['test_type']
        if 'order' in data:
            question.order = data['order']
        if 'is_active' in data:
            question.is_active = data['is_active']
            
        question.save()
        
        return JsonResponse({
            'success': True,
            'question': {
                'id': question.id,
                'text': question.text,
                'question_type': question.question_type,
                'test_type': question.test_type,
                'order': question.order,
                'is_active': question.is_active
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'errors': {'form': 'Неверный формат данных'}}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'errors': {'form': str(e)}}, status=500)

@require_http_methods(["DELETE"])
def delete_question(request, question_id):
    try:
        question = get_object_or_404(InterviewQuestion, id=question_id)
        question.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'errors': {'form': str(e)}}, status=500)