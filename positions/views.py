from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, ListView, UpdateView, DetailView
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.utils.decorators import method_decorator
import json
from django.core.serializers import serialize
from .models import Grade, Position, Parameter, ParameterDescription, PositionGrade, InterviewQuestion, ScoreMatrix, ScoreMatrixCell, ScoreMatrixSum, Interview, InterviewAnswer, InterviewResult
from .forms import GradeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.urls import reverse
import xlsxwriter
from io import BytesIO
from datetime import datetime
import pandas as pd
from .services import analyze_interview_results

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
            order=InterviewQuestion.objects.filter(position=position).count() + 1,
            is_active=data.get('is_active', True)
        )
        
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

@login_required
def score_matrices(request):
    """Список матриц пересчета баллов"""
    position_id = request.GET.get('position')
    matrices = ScoreMatrix.objects.select_related('position').all()
    
    if position_id:
        matrices = matrices.filter(position_id=position_id)
    
    # Добавляем информацию о количестве параметров и вопросов
    for matrix in matrices:
        matrix.parameters_count = Parameter.objects.filter(position=matrix.position).count()
        matrix.questions_count = InterviewQuestion.objects.filter(position=matrix.position).count()
    
    positions = Position.objects.all()
    selected_position = Position.objects.get(id=position_id) if position_id else None
    
    context = {
        'matrices': matrices,
        'positions': positions,
        'selected_position': selected_position
    }
    return render(request, 'positions/score_matrices.html', context)

@login_required
def create_score_matrix(request):
    """Создание новой матрицы пересчета баллов"""
    if request.method == 'POST':
        position_id = request.POST.get('position')
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        matrix = ScoreMatrix.objects.create(
            position_id=position_id,
            name=name,
            description=description
        )
        
        # Создаем пустые ячейки для всех комбинаций параметров и вопросов
        position = matrix.position
        parameters = Parameter.objects.filter(position=position)
        questions = InterviewQuestion.objects.filter(position=position)
        
        for parameter in parameters:
            for question in questions:
                ScoreMatrixCell.objects.create(
                    matrix=matrix,
                    parameter=parameter,
                    question=question,
                    score=0
                )
        
        return redirect('positions:edit_score_matrix', matrix_id=matrix.id)
    
    positions = Position.objects.all()
    return render(request, 'positions/create_score_matrix.html', {'positions': positions})

@login_required
def edit_score_matrix(request, matrix_id):
    """Редактирование матрицы пересчета баллов"""
    matrix = get_object_or_404(ScoreMatrix, id=matrix_id)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        parameter_id = data.get('parameter_id')
        question_id = data.get('question_id')
        score = data.get('score')
        
        try:
            cell = matrix.update_cell(parameter_id, question_id, score)
            matrix_data = matrix.get_matrix_data()
            return JsonResponse({
                'success': True,
                'matrix_data': matrix_data
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'errors': [str(e)]
            })
    
    # Получаем все параметры и вопросы для данной специализации
    parameters = Parameter.objects.filter(position=matrix.position)
    questions = InterviewQuestion.objects.filter(position=matrix.position)
    
    # Получаем существующие ячейки
    existing_cells = {
        (cell.parameter_id, cell.question_id): cell.score
        for cell in matrix.cells.all()
    }
    
    # Создаем только отсутствующие ячейки
    for parameter in parameters:
        for question in questions:
            if (parameter.id, question.id) not in existing_cells:
                ScoreMatrixCell.objects.create(
                    matrix=matrix,
                    parameter=parameter,
                    question=question,
                    score=0
                )
    
    # Получаем данные матрицы
    matrix_data = matrix.get_matrix_data()
    
    context = {
        'matrix': matrix,
        'matrix_data': matrix_data
    }
    return render(request, 'positions/edit_score_matrix.html', context)

@login_required
def delete_score_matrix(request, matrix_id):
    """Удаление матрицы пересчета баллов"""
    matrix = get_object_or_404(ScoreMatrix, id=matrix_id)
    
    if request.method == 'POST':
        matrix.delete()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Метод не поддерживается'})

@login_required
def toggle_matrix_active(request, matrix_id):
    """Переключение активности матрицы"""
    matrix = get_object_or_404(ScoreMatrix, id=matrix_id)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        matrix.is_active = data.get('is_active', False)
        matrix.save()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Метод не поддерживается'})

class InterviewCreateView(LoginRequiredMixin, CreateView):
    model = Interview
    template_name = 'positions/interview_create.html'
    fields = ['position', 'candidate_name', 'expected_grade', 'expected_salary', 'current_grade']
    success_url = '/interview/{pk}/conduct/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['positions'] = Position.objects.all()
        context['grades'] = Grade.objects.all()
        return context
    
    def get_success_url(self):
        return reverse('positions:interview_conduct', kwargs={'pk': self.object.pk})

class InterviewConductView(LoginRequiredMixin, UpdateView):
    model = Interview
    template_name = 'positions/interview_conduct.html'
    fields = []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        interview = self.get_object()
        questions = InterviewQuestion.objects.filter(position=interview.position)
        
        # Получаем или создаем ответы для каждого вопроса
        question_answers = []
        for question in questions:
            answer, created = InterviewAnswer.objects.get_or_create(
                interview=interview,
                question=question,
                defaults={'score': 0}
            )
            question_answers.append({
                'question': question,
                'answer': answer
            })
        
        context['question_answers'] = question_answers
        return context
    
    def post(self, request, *args, **kwargs):
        interview = self.get_object()
        answers = InterviewAnswer.objects.filter(interview=interview)
        
        # Обновляем баллы и заметки
        for answer in answers:
            score = request.POST.get(f'score_{answer.question.id}')
            notes = request.POST.get(f'notes_{answer.question.id}')
            if score is not None:
                answer.score = int(score)
            if notes is not None:
                answer.notes = notes
            answer.save()
        
        # Сохраняем общие заметки
        general_notes = request.POST.get('general_notes')
        if general_notes is not None:
            interview.general_notes = general_notes
            interview.save()
        
        # Получаем активную матрицу для позиции
        matrix = ScoreMatrix.objects.filter(position=interview.position, is_active=True).first()
        if not matrix:
            matrix = ScoreMatrix.objects.filter(position=interview.position).first()
        
        if matrix:
            matrix_data = matrix.get_matrix_data()
            print("Matrix data:", matrix_data)  # Отладочная информация
            
            # Удаляем все существующие результаты
            InterviewResult.objects.filter(interview=interview).delete()
            
            # Создаем новые результаты
            for parameter in Parameter.objects.filter(position=interview.position):
                total_score = 0
                print(f"\nProcessing parameter: {parameter.name} (ID: {parameter.id})")  # Отладочная информация
                
                for answer in answers:
                    # Получаем вес вопроса для данного параметра из матрицы
                    weight = matrix_data['cells'].get(parameter.id, {}).get(answer.question.id, 0)
                    print(f"Question: {answer.question.text} (ID: {answer.question.id})")  # Отладочная информация
                    print(f"Answer score: {answer.score}, Weight: {weight}")  # Отладочная информация
                    
                    # Добавляем взвешенный балл к общему результату
                    weighted_score = float(answer.score) * float(weight)
                    total_score += weighted_score
                    print(f"Weighted score: {weighted_score}, Running total: {total_score}")  # Отладочная информация
                
                # Создаем результат с округлением до 2 знаков после запятой
                final_score = round(total_score, 2)
                print(f"Final score for parameter {parameter.name}: {final_score}")
                
                # Создаем новый результат
                InterviewResult.objects.create(
                    interview=interview,
                    parameter=parameter,
                    score=final_score
                )
        
        return redirect('positions:interview_result', pk=interview.pk)

class InterviewResultView(LoginRequiredMixin, DetailView):
    model = Interview
    template_name = 'positions/interview_result.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        interview = self.get_object()
        
        # Получаем результаты по параметрам
        results = InterviewResult.objects.filter(interview=interview)
        
        # Округляем все баллы до 2 знаков после запятой
        for result in results:
            result.score = round(float(result.score), 2)
        
        total_score = round(float(results.aggregate(total=Sum('score'))['total'] or 0), 2)
        
        # Определяем грейд на основе суммы баллов
        position_grades = PositionGrade.objects.filter(
            position=interview.position
        ).select_related('grade').order_by('-grade__order')
        
        recommended_grade = None
        grade_change = None
        
        # Ищем первый грейд, для которого набранных баллов достаточно
        for position_grade in position_grades:
            if total_score >= position_grade.confirmation_points:
                recommended_grade = position_grade.grade
                if interview.current_grade:
                    if total_score >= position_grade.promotion_points:
                        grade_change = "повышение"
                    else:
                        grade_change = "подтверждение"
                break
        
        # Получаем активную матрицу для позиции
        matrix = ScoreMatrix.objects.filter(position=interview.position, is_active=True).first()
        if not matrix:
            matrix = ScoreMatrix.objects.filter(position=interview.position).first()
        
        # Подготовка данных для анализа
        results_data = []
        if matrix:
            matrix_data = matrix.get_matrix_data()
            
            # Получаем все ответы на вопросы
            answers = InterviewAnswer.objects.filter(
                interview=interview
            ).select_related('question')
            
            # Создаем словарь для хранения параметров вопросов
            question_parameters = {}
            for cell in matrix.cells.all():
                question_parameters[cell.question_id] = cell.parameter
            
            # Добавляем параметры к ответам
            for answer in answers:
                parameter = question_parameters.get(answer.question_id)
                if parameter:
                    results_data.append({
                        'parameter_name': parameter.name,
                        'question_text': answer.question.text,
                        'answer': answer.notes or '',
                        'score': float(answer.score)
                    })
        
        # Получаем анализ от Gemini AI
        try:
            ai_analysis = analyze_interview_results(results_data)
        except Exception as e:
            print(f"Error analyzing interview results: {e}")
            ai_analysis = "Не удалось получить рекомендации по развитию. Пожалуйста, попробуйте позже."
        
        # Получаем все ответы на вопросы для интервью с их параметрами
        answers_with_parameters = []
        if matrix:
            for answer in answers:
                parameter = question_parameters.get(answer.question_id)
                if parameter:
                    answers_with_parameters.append({
                        'answer': answer,
                        'parameter': parameter
                    })
        
        context.update({
            'results': results,
            'total_score': total_score,
            'grade': recommended_grade,
            'grade_change': grade_change,
            'answers': answers_with_parameters,
            'ai_analysis': ai_analysis
        })
        
        return context

class InterviewListView(LoginRequiredMixin, ListView):
    model = Interview
    template_name = 'positions/interview_list.html'
    context_object_name = 'interviews'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        position_id = self.request.GET.get('position')
        if position_id:
            queryset = queryset.filter(position_id=position_id)
        return queryset.select_related('position', 'expected_grade', 'current_grade').prefetch_related('results')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['positions'] = Position.objects.all()
        context['selected_position'] = self.request.GET.get('position')
        return context

@login_required
def download_interview_results(request, pk):
    """Скачивание результатов интервью в Excel"""
    interview = get_object_or_404(Interview, pk=pk)
    results = InterviewResult.objects.filter(interview=interview)
    
    # Создаем Excel файл в памяти
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()
    
    # Форматы
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#198754',
        'font_color': 'white',
        'border': 1
    })
    
    cell_format = workbook.add_format({
        'border': 1,
        'align': 'center'
    })
    
    # Заголовки
    headers = ['Параметр', 'Балл']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    
    # Данные
    for row, result in enumerate(results, start=1):
        worksheet.write(row, 0, result.parameter.name, cell_format)
        worksheet.write(row, 1, result.score, cell_format)
    
    # Общий балл
    total_row = len(results) + 2
    worksheet.write(total_row, 0, 'Общий балл', header_format)
    worksheet.write(total_row, 1, sum(r.score for r in results), cell_format)
    
    # Рекомендуемый грейд
    if interview.expected_grade:
        grade_row = total_row + 1
        worksheet.write(grade_row, 0, 'Рекомендуемый грейд', header_format)
        worksheet.write(grade_row, 1, interview.expected_grade.name, cell_format)
    
    # Настройка ширины столбцов
    worksheet.set_column('A:A', 30)
    worksheet.set_column('B:B', 15)
    
    workbook.close()
    output.seek(0)
    
    # Формируем имя файла
    filename = f'interview_results_{interview.candidate_name}_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
    
    # Создаем HTTP ответ
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@login_required
def download_score_matrix(request, matrix_id):
    """Выгрузка матрицы в Excel"""
    matrix = get_object_or_404(ScoreMatrix, id=matrix_id)
    matrix_data = matrix.get_matrix_data()
    
    # Создаем Excel файл в памяти
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()
    
    # Форматы
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#198754',
        'font_color': 'white',
        'border': 1,
        'align': 'center'
    })
    
    cell_format = workbook.add_format({
        'border': 1,
        'align': 'center'
    })
    
    # Заголовки
    worksheet.write(0, 0, 'Параметр \ Вопрос', header_format)
    for col, question in enumerate(matrix_data['questions'], start=1):
        worksheet.write(0, col, question['text'], header_format)
    worksheet.write(0, len(matrix_data['questions']) + 1, 'Сумма', header_format)
    
    # Данные
    for row, parameter in enumerate(matrix_data['parameters'], start=1):
        worksheet.write(row, 0, parameter['name'], cell_format)
        row_sum = 0
        for col, question in enumerate(matrix_data['questions'], start=1):
            score = matrix_data['cells'].get(parameter['id'], {}).get(question['id'], 0)
            worksheet.write(row, col, score, cell_format)
            row_sum += float(score)
        worksheet.write(row, len(matrix_data['questions']) + 1, row_sum, cell_format)
    
    # Суммы по столбцам
    worksheet.write(len(matrix_data['parameters']) + 1, 0, 'Сумма', header_format)
    for col, question in enumerate(matrix_data['questions'], start=1):
        col_sum = sum(float(matrix_data['cells'].get(param['id'], {}).get(question['id'], 0))
                     for param in matrix_data['parameters'])
        worksheet.write(len(matrix_data['parameters']) + 1, col, col_sum, cell_format)
    
    # Настройка ширины столбцов
    worksheet.set_column(0, 0, 30)  # Параметры
    for col in range(1, len(matrix_data['questions']) + 2):
        worksheet.set_column(col, col, 15)  # Вопросы и суммы
    
    workbook.close()
    output.seek(0)
    
    # Формируем имя файла
    filename = f'matrix_{matrix.name}_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
    
    # Создаем HTTP ответ
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@login_required
def upload_score_matrix(request, matrix_id):
    """Загрузка матрицы из Excel"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Метод не поддерживается'})
    
    matrix = get_object_or_404(ScoreMatrix, id=matrix_id)
    excel_file = request.FILES.get('excel_file')
    
    if not excel_file:
        return JsonResponse({'success': False, 'error': 'Файл не найден'})
    
    try:
        # Читаем Excel файл
        df = pd.read_excel(excel_file)
        
        # Получаем параметры и вопросы
        parameters = Parameter.objects.filter(position=matrix.position)
        questions = InterviewQuestion.objects.filter(position=matrix.position)
        
        # Проверяем соответствие структуры файла
        if len(df.columns) != len(questions) + 2:  # +2 для параметра и суммы
            return JsonResponse({
                'success': False,
                'error': 'Неверная структура файла. Количество столбцов не соответствует количеству вопросов.'
            })
        
        # Обновляем значения в матрице
        for index, row in df.iterrows():
            if index >= len(parameters):
                break
                
            parameter = parameters[index]
            for col, question in enumerate(questions, start=1):
                try:
                    score = float(row[col])
                    if 0 <= score <= 1:
                        matrix.update_cell(parameter.id, question.id, score)
                except (ValueError, TypeError):
                    continue
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["POST"])
def delete_interview(request, pk):
    """Удаление интервью"""
    interview = get_object_or_404(Interview, pk=pk)
    
    try:
        interview.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})