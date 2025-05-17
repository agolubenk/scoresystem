from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, ListView, UpdateView, DetailView, DeleteView
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.utils.decorators import method_decorator
import json
from django.core.serializers import serialize
from django import forms
from .models import Grade, Position, Parameter, ParameterDescription, PositionGrade, InterviewQuestion, ScoreMatrix, ScoreMatrixCell, ScoreMatrixSum, Interview, InterviewAnswer, InterviewResult, Candidate, TestAnswer, CandidateFile, CandidateTask, CandidateChangeHistory, CandidateComment, Vacancy, PositionProfile, VacancyGrade, PositionProfileGrade
from .forms import GradeForm, CandidateForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.urls import reverse, reverse_lazy
import xlsxwriter
from io import BytesIO
from datetime import datetime
import pandas as pd
from .services import analyze_interview_results
from django.views.decorators.csrf import csrf_exempt
import os
from dotenv import load_dotenv
from django.views import View
import re
import phonenumbers
from django.forms.models import model_to_dict
from django.core.files.storage import default_storage
from django.contrib import messages
import requests

load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

print('GEMINI_API_KEY:', GEMINI_API_KEY)

class GradeListView(ListView):
    model = Grade
    template_name = 'evaluation/grades.html'
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
    template_name = 'evaluation/grade_form.html'
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
    
    return render(request, 'evaluation/positions.html', {
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
    return render(request, 'evaluation/parameters.html', context)

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
    
    return render(request, 'evaluation/questions.html', context)

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
    return render(request, 'evaluation/score_matrices.html', context)

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
    return render(request, 'evaluation/create_score_matrix.html', {'positions': positions})

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
    return render(request, 'evaluation/edit_score_matrix.html', context)

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
    template_name = 'interview/interview_create.html'
    fields = ['position', 'candidate_name', 'expected_grade', 'expected_salary', 'current_grade']
    success_url = '/interview/{pk}/conduct/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['positions'] = Position.objects.all()
        context['grades'] = Grade.objects.all()
        context['candidates'] = Candidate.objects.all()
        return context
    
    def get_success_url(self):
        return reverse('positions:interview_conduct', kwargs={'pk': self.object.pk})

class InterviewConductView(LoginRequiredMixin, UpdateView):
    model = Interview
    template_name = 'interview/interview_conduct.html'
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
    template_name = 'interview/interview_result.html'
    
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
            ai_analysis = {
                'summary': 'Нет данных',
                'strengths': 'Нет данных',
                'areas': 'Нет данных',
                'recommendations': 'Нет данных',
                'conclusion': 'Нет данных',
            }
        
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
    template_name = 'interview/interview_list.html'
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
    worksheet.write(0, 0, 'Параметр \\ Вопрос', header_format)
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

@require_POST
def rerun_ai_analysis(request, pk):
    from .models import Interview, InterviewResult, InterviewAnswer, ScoreMatrix
    try:
        interview = Interview.objects.get(pk=pk)
        matrix = ScoreMatrix.objects.filter(position=interview.position, is_active=True).first()
        if not matrix:
            matrix = ScoreMatrix.objects.filter(position=interview.position).first()
        results_data = []
        if matrix:
            matrix_data = matrix.get_matrix_data()
            answers = InterviewAnswer.objects.filter(interview=interview).select_related('question')
            question_parameters = {}
            for cell in matrix.cells.all():
                question_parameters[cell.question_id] = cell.parameter
            for answer in answers:
                parameter = question_parameters.get(answer.question_id)
                if parameter:
                    results_data.append({
                        'parameter_name': parameter.name,
                        'question_text': answer.question.text,
                        'answer': answer.notes or '',
                        'score': float(answer.score)
                    })
        ai_analysis = analyze_interview_results(results_data)
        # Формируем HTML для шаблона
        html = f"""
        <div><b>1. Общий анализ результатов:</b><br>{ai_analysis['summary']}</div>
        <div class='mt-2'><b>2. Сильные стороны:</b><br>{ai_analysis['strengths']}</div>
        <div class='mt-2'><b>3. Области для развития:</b><br>{ai_analysis['areas']}</div>
        <div class='mt-2'><b>4. Конкретные рекомендации по улучшению:</b><br>{ai_analysis['recommendations']}</div>
        <div class='mt-2'><b>Финальное заключение:</b><br>{ai_analysis['conclusion']}</div>
        """
        return JsonResponse({'success': True, 'analysis': html})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

class CandidateListView(LoginRequiredMixin, ListView):
    model = Candidate
    template_name = 'candidates/candidate_list.html'
    context_object_name = 'candidates'
    paginate_by = 20
    
    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(full_name__icontains=q)
        return qs.order_by('full_name')

class CandidateCreateView(LoginRequiredMixin, CreateView):
    model = Candidate
    form_class = CandidateForm
    template_name = 'candidates/candidate_form.html'
    success_url = reverse_lazy('positions:candidate_list')

class CandidateUpdateView(LoginRequiredMixin, UpdateView):
    model = Candidate
    form_class = CandidateForm
    template_name = 'candidates/candidate_form.html'
    success_url = reverse_lazy('positions:candidate_list')

class CandidateDetailView(LoginRequiredMixin, DetailView):
    model = Candidate
    template_name = 'candidates/candidate_detail.html'
    context_object_name = 'candidate'

class CandidateDeleteView(LoginRequiredMixin, DeleteView):
    model = Candidate
    template_name = 'candidates/candidate_confirm_delete.html'
    success_url = reverse_lazy('positions:candidate_list')

class CandidateResumePreviewView(View):
    def get(self, request, pk):
        candidate = get_object_or_404(Candidate, pk=pk)
        if not candidate.resume:
            return HttpResponse('Резюме не найдено', status=404)
        file_path = candidate.resume.path
        if not os.path.exists(file_path):
            return HttpResponse('Файл не найден на сервере', status=404)
        response = FileResponse(open(file_path, 'rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{candidate.resume.name}"'
        return response

def candidate_resume_view(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    resume_exists = candidate.resume and candidate.resume.name and os.path.exists(candidate.resume.path)
    if request.method == 'POST' and request.FILES.get('resume'):
        resume = request.FILES['resume']
        candidate.resume.save(resume.name, resume, save=True)
        return redirect('positions:candidate_resume_view', pk=pk)
    return render(request, 'candidates/candidate_resume_view.html', {'candidate': candidate, 'resume_exists': resume_exists})

@require_POST
@login_required
def update_test_template(request, question_id):
    try:
        question = InterviewQuestion.objects.get(id=question_id)
        if question.question_type != 'test':
            return JsonResponse({'success': False, 'error': 'Это не тестовый вопрос'})
        
        # Обновляем текст вопроса
        question.text = request.POST.get('text')
        question.test_type = request.POST.get('test_type')
        question.save()
        
        # Обновляем варианты ответов
        answers = request.POST.getlist('answers[]')
        is_correct = request.POST.getlist('is_correct[]')
        
        # Удаляем старые варианты ответов
        question.answers.all().delete()
        
        # Создаем новые варианты ответов
        for i, answer_text in enumerate(answers):
            if answer_text.strip():  # Пропускаем пустые ответы
                TestAnswer.objects.create(
                    question=question,
                    text=answer_text,
                    is_correct=str(i) in is_correct,
                    order=i
                )
        
        return JsonResponse({'success': True})
    except InterviewQuestion.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Вопрос не найден'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def candidate_files_upload(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    files = request.FILES.getlist('files')
    errors = []
    uploaded = []
    for f in files:
        try:
            CandidateFile.objects.create(candidate=candidate, file=f)
            uploaded.append(f.name)
            # История изменений
            CandidateChangeHistory.objects.create(
                candidate=candidate,
                field='file',
                old_value='',
                new_value=f'Загружен файл: {f.name}'
            )
        except Exception as e:
            errors.append(f"{f.name}: {str(e)}")
    if errors:
        return JsonResponse({'success': False, 'uploaded': uploaded, 'errors': errors, 'error': 'Не удалось загрузить некоторые файлы'})
    return JsonResponse({'success': True, 'uploaded': uploaded})

def candidate_detail(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    positions = Position.objects.all()
    files = []
    for f in candidate.files.all():
        fname = f.file.name.split('/')[-1]
        ext = fname.lower().split('.')[-1] if '.' in fname else ''
        files.append({'id': f.id, 'url': f.file.url, 'name': fname, 'ext': ext, 'uploaded_at': f.uploaded_at})

    # Собираем все имена, которые когда-либо были у кандидата (для интервью)
    names = set([candidate.full_name])
    for ch in candidate.change_history.filter(field='full_name'):
        if ch.old_value:
            names.add(ch.old_value)
        if ch.new_value:
            names.add(ch.new_value)

    # Получаем все интервью по этим именам
    interviews_qs = Interview.objects.filter(
        candidate_name__in=names
    ).select_related('position', 'expected_grade').order_by('-created_at')

    # Для каждой карточки интервью собираем рекомендуемый грейд и общий балл
    interviews = []
    for interview in interviews_qs:
        # Общий балл
        results = InterviewResult.objects.filter(interview=interview)
        total_score = round(float(results.aggregate(total=Sum('score'))['total'] or 0), 2)
        # Рекомендованный грейд
        position_grades = PositionGrade.objects.filter(
            position=interview.position
        ).select_related('grade').order_by('-grade__order')
        recommended_grade = None
        for position_grade in position_grades:
            if total_score >= position_grade.confirmation_points:
                recommended_grade = position_grade.grade
                break
        interviews.append({
            'type': 'interview',
            'id': interview.pk,
            'position': interview.position,
            'expected_grade': interview.expected_grade,
            'recommended_grade': recommended_grade,
            'total_score': total_score,
            'created_at': interview.created_at,
        })

    # История изменений кандидата
    change_history = [
        {
            'type': 'change',
            'field': ch.field,
            'old_value': ch.old_value,
            'new_value': ch.new_value,
            'changed_at': ch.changed_at,
        }
        for ch in candidate.change_history.all()
    ]

    # Комментарии
    comments = [
        {
            'type': 'comment',
            'id': c.id,
            'author': c.author.get_full_name() or c.author.username if c.author else '—',
            'author_id': c.author.id if c.author else None,
            'text': c.text,
            'created_at': c.created_at,
            'can_edit': (request.user.is_authenticated and c.author and c.author.id == request.user.id),
        }
        for c in candidate.comments.all()
    ]

    # Событие создания кандидата
    created_event = {
        'type': 'created',
        'created_at': candidate.created_at,
    }

    # Объединяем все события и сортируем по дате
    history_events = [created_event]
    for ch in change_history:
        ch['date'] = ch['changed_at']
        history_events.append(ch)
    for comment in comments:
        comment['date'] = comment['created_at']
        history_events.append(comment)
    for interview in interviews:
        interview['date'] = interview['created_at']
        history_events.append(interview)
    history_events = sorted(history_events, key=lambda x: x.get('date') or x.get('created_at'))

    # Считаем количество комментариев и интервью
    comments_count = sum(1 for e in history_events if e.get('type') == 'comment')
    interviews_count = sum(1 for e in history_events if e.get('type') == 'interview')

    return render(request, 'positions/candidate_detail.html', {
        'candidate': candidate,
        'positions': positions,
        'candidate_files': files,
        'interviews': interviews,  # для обратной совместимости, можно убрать позже
        'change_history': change_history,  # для обратной совместимости, можно убрать позже
        'history_events': history_events,
        'comments_count': comments_count,
        'interviews_count': interviews_count,
    })

@require_http_methods(["POST"])
def candidate_file_delete(request, file_id):
    file = get_object_or_404(CandidateFile, id=file_id)
    candidate = file.candidate
    file_name = file.file.name.split('/')[-1]
    file.file.delete(save=False)
    file.delete()
    # История изменений
    CandidateChangeHistory.objects.create(
        candidate=candidate,
        field='file',
        old_value=f'Удалён файл: {file_name}',
        new_value=''
    )
    return JsonResponse({'success': True})

@require_http_methods(["POST"])
def candidate_update(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    field = None
    value = None

    # Определяем, какое поле редактируется
    for f in ['full_name', 'email', 'phone', 'telegram', 'desired_position', 'notes']:
        if f in request.POST:
            field = f
            value = request.POST.get(f)
            break
    if 'resume' in request.FILES:
        field = 'resume'
        value = request.FILES['resume']

    if not field:
        return JsonResponse({'success': False, 'error': 'Нет данных для обновления'})

    # Валидация и обновление
    try:
        old_value = None
        new_value_for_history = value
        if field == 'full_name':
            old_value = candidate.full_name
            candidate.full_name = value
        elif field == 'email':
            old_value = candidate.email
            if value and '@' not in value:
                return JsonResponse({'success': False, 'error': 'Некорректный email'})
            candidate.email = value
        elif field == 'phone':
            old_value = candidate.phone
            if value:
                try:
                    phone_obj = phonenumbers.parse(value, None)
                    if not phonenumbers.is_valid_number(phone_obj):
                        return JsonResponse({'success': False, 'error': 'Некорректный номер телефона для страны'})
                except Exception as e:
                    return JsonResponse({'success': False, 'error': f'Ошибка валидации номера: {str(e)}'})
            candidate.phone = value
        elif field == 'telegram':
            old_value = candidate.telegram
            candidate.telegram = value
        elif field == 'desired_position':
            old_value = candidate.desired_position.name if candidate.desired_position else None
            if value:
                try:
                    candidate.desired_position = Position.objects.get(pk=value)
                except Position.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Должность не найдена'})
            else:
                candidate.desired_position = None
            new_value_for_history = candidate.desired_position.name if candidate.desired_position else None
        elif field == 'notes':
            old_value = candidate.notes
            candidate.notes = value
        elif field == 'resume':
            old_value = candidate.resume.name if candidate.resume else None
            candidate.resume = value
        else:
            return JsonResponse({'success': False, 'error': 'Неизвестное поле'})
        candidate.save()
        # Сохраняем историю изменений только если значение реально изменилось
        if field != 'resume' and (str(old_value) != str(new_value_for_history)):
            CandidateChangeHistory.objects.create(
                candidate=candidate,
                field=field,
                old_value=old_value,
                new_value=new_value_for_history
            )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["GET", "POST"])
def candidate_tasks(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    if request.method == "GET":
        tasks = candidate.tasks.order_by('-created_at')
        return JsonResponse({
            'tasks': [
                {
                    'id': t.id,
                    'title': t.title,
                    'description': t.description,
                    'due_date': t.due_date.strftime('%Y-%m-%d') if t.due_date else '',
                    'is_completed': t.is_completed,
                } for t in tasks
            ]
        })
    elif request.method == "POST":
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        due_date = data.get('due_date')
        if not title:
            return JsonResponse({'success': False, 'error': 'Название задачи обязательно'}, status=400)
        task = CandidateTask.objects.create(
            candidate=candidate,
            title=title,
            description=description,
            due_date=due_date or None
        )
        return JsonResponse({'success': True, 'task': model_to_dict(task)})

@login_required
@require_http_methods(["POST"])
def add_candidate_comment(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    text = request.POST.get('text', '').strip()
    if not text:
        return JsonResponse({'success': False, 'error': 'Комментарий не может быть пустым'})
    comment = CandidateComment.objects.create(
        candidate=candidate,
        author=request.user,
        text=text
    )
    return JsonResponse({
        'success': True,
        'author': comment.author.get_full_name() or comment.author.username,
        'text': comment.text,
        'created_at': comment.created_at.strftime('%d.%m.%Y %H:%M')
    })

@csrf_exempt
@login_required
def edit_candidate_comment(request, comment_id):
    import json
    try:
        comment = CandidateComment.objects.get(id=comment_id)
        if comment.author != request.user:
            return JsonResponse({'success': False, 'error': 'Нет прав на редактирование'}, status=403)
        data = json.loads(request.body)
        text = data.get('text', '').strip()
        if not text:
            return JsonResponse({'success': False, 'error': 'Комментарий не может быть пустым'})
        comment.text = text
        comment.save()
        return JsonResponse({'success': True, 'text': comment.text})
    except CandidateComment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Комментарий не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

def index(request):
    return render(request, 'evaluation/index.html')

@csrf_exempt
def reorder_grades(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            for item in data.get('order', []):
                grade = Grade.objects.get(id=item['id'])
                grade.order = item['order']
                grade.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid method'})

@login_required
def export_parameters_excel(request):
    """Выгрузка параметров и описаний в Excel"""
    grades = list(Grade.objects.all().order_by('order'))
    parameters = Parameter.objects.all().order_by('name')
    data = []
    for param in parameters:
        row = {'Параметр': param.name, 'Специализация': param.position.name if param.position else ''}
        for grade in grades:
            desc = ParameterDescription.objects.filter(parameter=param, grade=grade).first()
            row[grade.name] = desc.description if desc else ''
        data.append(row)
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Параметры')
    output.seek(0)
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=parameters.xlsx'
    return response

@login_required
@require_http_methods(["POST"])
def import_parameters_excel(request):
    """Загрузка параметров и описаний из Excel"""
    excel_file = request.FILES.get('file')
    if not excel_file:
        return JsonResponse({'success': False, 'error': 'Файл не передан'})
    try:
        df = pd.read_excel(excel_file)
        grades = {g.name: g for g in Grade.objects.all()}
        for _, row in df.iterrows():
            param_name = str(row.get('Параметр', '')).strip()
            position_name = str(row.get('Специализация', '')).strip()
            if not param_name:
                continue
            position = Position.objects.filter(name=position_name).first() if position_name else None
            param, _ = Parameter.objects.get_or_create(name=param_name, defaults={'position': position})
            if position and param.position != position:
                param.position = position
                param.save()
            for grade_name, grade in grades.items():
                if grade_name in row:
                    desc_text = str(row[grade_name]).strip()
                    if desc_text and desc_text != 'nan':
                        desc, _ = ParameterDescription.objects.get_or_create(parameter=param, grade=grade)
                        desc.description = desc_text
                        desc.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

class VacancyForm(forms.ModelForm):
    class Meta:
        model = Vacancy
        fields = ['name', 'position', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class PositionProfileForm(forms.ModelForm):
    class Meta:
        model = PositionProfile
        fields = ['profile_text']
        widgets = {
            'profile_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
        }

@login_required
def vacancies_list(request):
    show_profiles = request.GET.get('profiles')
    grade_id = request.GET.get('grade')
    position_id = request.GET.get('position')
    vacancy_grades = VacancyGrade.objects.select_related('vacancy', 'grade', 'vacancy__position', 'vacancy__profile')
    if show_profiles:
        vacancy_grades = vacancy_grades.filter(vacancy__profile__isnull=False)
    if grade_id:
        vacancy_grades = vacancy_grades.filter(grade_id=grade_id)
    if position_id:
        vacancy_grades = vacancy_grades.filter(vacancy__position_id=position_id)
    grades = Grade.objects.all()
    positions = Position.objects.all()
    return render(request, 'evaluation/vacancies_list.html', {
        'vacancy_grades': vacancy_grades,
        'grades': grades,
        'positions': positions,
        'selected_grade': grade_id,
        'selected_position': position_id,
        'show_profiles': show_profiles,
    })

@login_required
def vacancy_detail(request, pk):
    vacancy = get_object_or_404(Vacancy, pk=pk)
    grades = Grade.objects.all()
    vacancy_grades = VacancyGrade.objects.filter(vacancy=vacancy).select_related('grade')
    return render(request, 'evaluation/vacancy_detail.html', {
        'vacancy': vacancy,
        'vacancy_grades': vacancy_grades,
        'grades': grades,
    })

@login_required
def vacancy_create(request):
    if request.method == 'POST':
        form = VacancyForm(request.POST)
        if form.is_valid():
            vacancy = form.save()
            messages.success(request, 'Вакансия успешно создана.')
            return redirect('positions:vacancy_detail', pk=vacancy.pk)
    else:
        form = VacancyForm()
    return render(request, 'evaluation/vacancy_form.html', {'form': form})

@login_required
def vacancy_edit(request, pk):
    vacancy = get_object_or_404(Vacancy, pk=pk)
    if request.method == 'POST':
        form = VacancyForm(request.POST, instance=vacancy)
        if form.is_valid():
            form.save()
            messages.success(request, 'Вакансия обновлена.')
            return redirect('positions:vacancy_detail', pk=vacancy.pk)
    else:
        form = VacancyForm(instance=vacancy)
    return render(request, 'evaluation/vacancy_form.html', {'form': form, 'vacancy': vacancy})

@login_required
def vacancy_delete(request, pk):
    vacancy = get_object_or_404(Vacancy, pk=pk)
    if request.method == 'POST':
        vacancy.delete()
        messages.success(request, 'Вакансия удалена.')
        return redirect('positions:vacancies_list')
    return render(request, 'evaluation/vacancy_confirm_delete.html', {'vacancy': vacancy})

@login_required
def profile_detail(request, vacancy_id):
    vacancy = get_object_or_404(Vacancy, pk=vacancy_id)
    profile = getattr(vacancy, 'profile', None)
    grades = Grade.objects.all()
    positions = Position.objects.all()
    profile_grades = []
    if profile:
        profile_grades = list(profile.grade_profiles.select_related('grade').order_by('grade__order'))
        for pg in profile_grades:
            hard_skills = pg.hard_skills.split('\n') if pg.hard_skills else []
            hard_levels = pg.hard_level.split('\n') if pg.hard_level else []
            pg.hard_skills_table = list(zip(hard_skills, hard_levels))
            soft_skills = pg.soft_meta_skills.split('\n') if pg.soft_meta_skills else []
            soft_levels = pg.hard_requirements.split('\n') if pg.hard_requirements else []
            pg.soft_meta_skills_table = list(zip(soft_skills, soft_levels))
    def is_profile_grade_filled(pg):
        def has_nonempty_skill(skills_str):
            if not skills_str:
                return False
            return any(s.strip() for s in skills_str.split('\n'))
        filled = bool(
            pg.general_description and pg.general_description.strip() and
            has_nonempty_skill(pg.hard_skills) and
            has_nonempty_skill(pg.soft_meta_skills) and
            pg.notes and pg.notes.strip()
        )
        return filled
    need_ai_generate = any(not is_profile_grade_filled(pg) for pg in profile_grades)
    return render(request, 'evaluation/profile_detail.html', {
        'vacancy': vacancy,
        'profile': profile,
        'grades': grades,
        'positions': positions,
        'profile_grades': profile_grades,
        'need_ai_generate': need_ai_generate,
    })

@login_required
def profile_edit(request, vacancy_id):
    vacancy = get_object_or_404(Vacancy, pk=vacancy_id)
    profile, created = PositionProfile.objects.get_or_create(vacancy=vacancy)
    if request.method == 'POST':
        form = PositionProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль должности сохранён.')
            return redirect('positions:profile_detail', vacancy_id=vacancy.pk)
    else:
        form = PositionProfileForm(instance=profile)
    return render(request, 'evaluation/profile_form.html', {'form': form, 'vacancy': vacancy, 'profile': profile})

def ensure_profile_grades():
    from .models import PositionProfile, Grade, PositionProfileGrade
    for profile in PositionProfile.objects.all():
        vacancy = profile.vacancy
        for grade in Grade.objects.all():
            if not PositionProfileGrade.objects.filter(profile=profile, vacancy=vacancy, grade=grade).exists():
                PositionProfileGrade.objects.create(profile=profile, vacancy=vacancy, grade=grade)

@login_required
def profiles_list(request):
    ensure_profile_grades()
    grade_id = request.GET.get('grade')
    position_id = request.GET.get('position')
    profile_grades = PositionProfileGrade.objects.select_related('profile', 'grade', 'vacancy', 'vacancy__position')
    if grade_id:
        profile_grades = profile_grades.filter(grade_id=grade_id)
    if position_id:
        profile_grades = profile_grades.filter(vacancy__position_id=position_id)
    grades = Grade.objects.all()
    positions = Position.objects.all()
    return render(request, 'evaluation/profiles_list.html', {
        'profile_grades': profile_grades,
        'grades': grades,
        'positions': positions,
        'selected_grade': grade_id,
        'selected_position': position_id,
    })

@csrf_exempt
@require_POST
def update_profile_grade_field(request):
    import json
    from .models import PositionProfileGrade
    data = json.loads(request.body)
    obj_id = data.get('id')
    field = data.get('field')
    value = data.get('value')
    try:
        # --- Массовое обновление supervisor ---
        if field == 'supervisor' and isinstance(obj_id, list):
            PositionProfileGrade.objects.filter(id__in=obj_id).update(supervisor=value)
            return JsonResponse({'success': True, 'value': value})
        # --- Обычное поведение ---
        obj = PositionProfileGrade.objects.get(id=obj_id)
        # --- Работа с hard/soft skills как списками ---
        if field.startswith('hard_skill_') or field.startswith('hard_level_'):
            # Индекс или 'new'
            idx = field.split('_')[-1]
            skills = obj.hard_skills.split('\n') if obj.hard_skills else []
            levels = obj.hard_level.split('\n') if obj.hard_level else []
            if field.startswith('hard_skill_'):
                if idx == 'new':
                    skills.append(value)
                    levels.append('')
                else:
                    idx = int(idx)
                    while len(skills) <= idx:
                        skills.append('')
                    skills[idx] = value
                obj.hard_skills = '\n'.join(skills)
                obj.hard_level = '\n'.join(levels)
                obj.save()
                return JsonResponse({'success': True, 'value': value})
            elif field.startswith('hard_level_'):
                if idx == 'new':
                    levels.append(value)
                    skills.append('')
                else:
                    idx = int(idx)
                    while len(levels) <= idx:
                        levels.append('')
                    levels[idx] = value
                obj.hard_skills = '\n'.join(skills)
                obj.hard_level = '\n'.join(levels)
                obj.save()
                return JsonResponse({'success': True, 'value': value})
        elif field == 'hard_remove_row':
            idx = int(value)
            skills = obj.hard_skills.split('\n') if obj.hard_skills else []
            levels = obj.hard_level.split('\n') if obj.hard_level else []
            if idx < len(skills):
                skills.pop(idx)
            if idx < len(levels):
                levels.pop(idx)
            obj.hard_skills = '\n'.join(skills)
            obj.hard_level = '\n'.join(levels)
            obj.save()
            return JsonResponse({'success': True})
        elif field.startswith('soft_skill_') or field.startswith('soft_level_'):
            idx = field.split('_')[-1]
            skills = obj.soft_meta_skills.split('\n') if obj.soft_meta_skills else []
            levels = obj.hard_requirements.split('\n') if obj.hard_requirements else []
            if field.startswith('soft_skill_'):
                if idx == 'new':
                    skills.append(value)
                    levels.append('')
                else:
                    idx = int(idx)
                    while len(skills) <= idx:
                        skills.append('')
                    skills[idx] = value
                obj.soft_meta_skills = '\n'.join(skills)
                obj.hard_requirements = '\n'.join(levels)
                obj.save()
                return JsonResponse({'success': True, 'value': value})
            elif field.startswith('soft_level_'):
                if idx == 'new':
                    levels.append(value)
                    skills.append('')
                else:
                    idx = int(idx)
                    while len(levels) <= idx:
                        levels.append('')
                    levels[idx] = value
                obj.soft_meta_skills = '\n'.join(skills)
                obj.hard_requirements = '\n'.join(levels)
                obj.save()
                return JsonResponse({'success': True, 'value': value})
        elif field == 'soft_remove_row':
            idx = int(value)
            skills = obj.soft_meta_skills.split('\n') if obj.soft_meta_skills else []
            levels = obj.hard_requirements.split('\n') if obj.hard_requirements else []
            if idx < len(skills):
                skills.pop(idx)
            if idx < len(levels):
                levels.pop(idx)
            obj.soft_meta_skills = '\n'.join(skills)
            obj.hard_requirements = '\n'.join(levels)
            obj.save()
            return JsonResponse({'success': True})
        # --- Сохранение зарплаты и руководителя ---
        elif field in ['salary_min', 'salary_max']:
            if value == '' or value is None:
                setattr(obj, field, None)
            else:
                setattr(obj, field, value)
            obj.save()
            return JsonResponse({'success': True, 'value': getattr(obj, field)})
        elif field == 'supervisor':
            obj.supervisor = value
            obj.save()
            return JsonResponse({'success': True, 'value': obj.supervisor})
        # --- Остальные поля ---
        elif hasattr(obj, field):
            setattr(obj, field, value)
            obj.save()
            return JsonResponse({'success': True, 'value': getattr(obj, field)})
        else:
            return JsonResponse({'success': False, 'error': 'Нет такого поля'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_POST
def update_vacancy_grade_field(request):
    import json
    from .models import VacancyGrade
    data = json.loads(request.body)
    obj_id = data.get('id')
    field = data.get('field')
    value = data.get('value')
    try:
        obj = VacancyGrade.objects.get(id=obj_id)
        if hasattr(obj, field):
            setattr(obj, field, value)
            obj.save()
            return JsonResponse({'success': True, 'value': getattr(obj, field)})
        else:
            return JsonResponse({'success': False, 'error': 'Нет такого поля'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_POST
def update_vacancy_field(request):
    import json
    from .models import Vacancy
    data = json.loads(request.body)
    obj_id = data.get('id')
    field = data.get('field')
    value = data.get('value')
    try:
        obj = Vacancy.objects.get(id=obj_id)
        if hasattr(obj, field):
            setattr(obj, field, value)
            obj.save()
            return JsonResponse({'success': True, 'value': getattr(obj, field)})
        else:
            return JsonResponse({'success': False, 'error': 'Нет такого поля'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_GET
@login_required
def download_profile_grades_excel(request, vacancy_id):
    from .models import Vacancy, PositionProfileGrade
    vacancy = get_object_or_404(Vacancy, pk=vacancy_id)
    profile = getattr(vacancy, 'profile', None)
    if not profile:
        return JsonResponse({'success': False, 'error': 'Профиль не найден'}, status=404)
    profile_grades = profile.grade_profiles.select_related('grade').order_by('grade__order')
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    # Стили
    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center'})
    table_header_fmt = workbook.add_format({'bold': True, 'bg_color': '#B7DEE8', 'border': 1, 'align': 'center'})
    cell_fmt = workbook.add_format({'border': 1, 'align': 'left'})
    for pg in profile_grades:
        sheet_name = pg.grade.name[:31]
        ws = workbook.add_worksheet(sheet_name)
        row = 0
        # Общее описание (объединённая)
        ws.merge_range(row, 0, row, 2, 'Общее описание', header_fmt)
        row += 1
        ws.merge_range(row, 0, row, 2, pg.general_description or '', cell_fmt)
        row += 2
        # Hard skills (объединённая)
        ws.merge_range(row, 0, row, 2, 'Hard skills', header_fmt)
        row += 1
        ws.write(row, 0, 'Навык', table_header_fmt)
        ws.write(row, 1, 'Уровень владения', table_header_fmt)
        hard_skills = pg.hard_skills.split('\n') if pg.hard_skills else []
        hard_levels = pg.hard_level.split('\n') if pg.hard_level else []
        max_hard = max(len(hard_skills), len(hard_levels))
        for i in range(max_hard):
            ws.write(row + 1 + i, 0, hard_skills[i] if i < len(hard_skills) else '', cell_fmt)
            ws.write(row + 1 + i, 1, hard_levels[i] if i < len(hard_levels) else '', cell_fmt)
        row += 1 + max_hard + 1
        # Soft & Meta skills (объединённая)
        ws.merge_range(row, 0, row, 2, 'Soft & Meta skills', header_fmt)
        row += 1
        ws.write(row, 0, 'Навык', table_header_fmt)
        ws.write(row, 1, 'Уровень владения', table_header_fmt)
        soft_skills = pg.soft_meta_skills.split('\n') if pg.soft_meta_skills else []
        soft_levels = pg.hard_requirements.split('\n') if pg.hard_requirements else []
        max_soft = max(len(soft_skills), len(soft_levels))
        for i in range(max_soft):
            ws.write(row + 1 + i, 0, soft_skills[i] if i < len(soft_skills) else '', cell_fmt)
            ws.write(row + 1 + i, 1, soft_levels[i] if i < len(soft_levels) else '', cell_fmt)
        row += 1 + max_soft + 1
        # Пояснения (объединённая)
        ws.merge_range(row, 0, row, 2, 'Пояснения', header_fmt)
        row += 1
        ws.merge_range(row, 0, row, 2, pg.notes or '', cell_fmt)
        row += 2
        # Зарплата (объединённая)
        ws.merge_range(row, 0, row, 2, 'Зарплата', header_fmt)
        row += 1
        ws.write(row, 0, 'от', table_header_fmt)
        ws.write(row, 1, str(pg.salary_min) if hasattr(pg, 'salary_min') and pg.salary_min is not None else '', cell_fmt)
        ws.write(row, 2, 'до', table_header_fmt)
        ws.write(row, 3, str(pg.salary_max) if hasattr(pg, 'salary_max') and pg.salary_max is not None else '', cell_fmt)
        row += 2
        # Руководитель (объединённая)
        ws.merge_range(row, 0, row, 2, 'Руководитель', header_fmt)
        row += 1
        ws.merge_range(row, 0, row, 2, pg.supervisor if hasattr(pg, 'supervisor') else '', cell_fmt)
    workbook.close()
    output.seek(0)
    filename = f'profile_grades_{vacancy_id}.xlsx'
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@csrf_exempt
@login_required
@require_POST
def generate_profile_grades_ai(request, vacancy_id):
    """
    Генерирует профили должности для всех грейдов с помощью Gemini API, последовательно,
    если есть незаполненные поля (general_description, hard/soft skills, notes).
    """
    from .models import Vacancy, PositionProfileGrade, Grade, Parameter, ParameterDescription
    vacancy = get_object_or_404(Vacancy, pk=vacancy_id)
    profile = getattr(vacancy, 'profile', None)
    if not profile:
        return JsonResponse({'success': False, 'error': 'Профиль не найден'})
    profile_grades = list(profile.grade_profiles.select_related('grade').order_by('grade__order'))
    if not profile_grades:
        return JsonResponse({'success': False, 'error': 'Нет грейдов для профиля'})
    # Проверяем, есть ли незаполненные поля
    need_generate = False
    for pg in profile_grades:
        if not (pg.general_description and pg.hard_skills and pg.soft_meta_skills and pg.notes):
            need_generate = True
            break
    if not need_generate:
        return JsonResponse({'success': False, 'error': 'Все профили уже заполнены'})
    # Собираем параметры по грейдам
    grades = Grade.objects.all().order_by('order')
    parameters_by_grade = {}
    for grade in grades:
        params = ParameterDescription.objects.filter(grade=grade, parameter__position=vacancy.position)
        parameters_by_grade[grade.id] = [p.description for p in params if p.description]
    # Последовательная генерация
    prev_profile = None
    for idx, pg in enumerate(profile_grades):
        # Если все поля заполнены — пропускаем
        if pg.general_description and pg.hard_skills and pg.soft_meta_skills and pg.notes:
            prev_profile = pg  # для цепочки
            continue
        grade = pg.grade
        params = parameters_by_grade.get(grade.id, [])
        # Формируем промпт
        prompt = f"""
        Сгенерируй профиль должности для грейда "{grade.name}" по специализации "{vacancy.position.name}".
        Параметры для этого грейда:
        {chr(10).join(params) if params else 'Нет параметров'}
        """
        if prev_profile:
            prompt += f"\nУчитывай, что для предыдущего грейда профиль был такой:\nОписание: {prev_profile.general_description}\nHard skills: {prev_profile.hard_skills}\nSoft/meta skills: {prev_profile.soft_meta_skills}\nПояснения: {prev_profile.notes}"
        prompt += "\nОтвет верни в формате JSON с ключами: general_description, hard_skills (список), soft_meta_skills (список), notes."
        # Запрос к Gemini
        api_key = GEMINI_API_KEY
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + api_key
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=60)
            try:
                resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                print('Gemini API error:', resp.status_code, resp.text)
                return JsonResponse({'success': False, 'error': f'Gemini API error: {str(e)}', 'response': resp.text})
            result = resp.json()
            print('Gemini raw response:', repr(result))
            if not result.get('candidates'):
                return JsonResponse({'success': False, 'error': f'Gemini не вернул кандидатов: {result}'})
            text = result['candidates'][0]['content']['parts'][0].get('text', '')
            if not text.strip():
                return JsonResponse({'success': False, 'error': f'Gemini вернул пустой текст: {repr(text)}'})
            # Удаляем markdown-обёртку, если есть
            text = text.strip()
            if text.startswith('```json'):
                text = text[len('```json'):].strip()
            if text.startswith('```'):
                text = text[len('```'):].strip()
            if text.endswith('```'):
                text = text[:-3].strip()
            import json as pyjson
            parsed = pyjson.loads(text)
            pg.general_description = parsed.get('general_description', '')
            pg.hard_skills = '\n'.join(parsed.get('hard_skills', []))
            pg.soft_meta_skills = '\n'.join(parsed.get('soft_meta_skills', []))
            pg.notes = parsed.get('notes', '')
            pg.save()
            prev_profile = pg
        except Exception as e:
            print('Ошибка генерации Gemini:', str(e))
            return JsonResponse({'success': False, 'error': f'Ошибка генерации для грейда {grade.name}: {str(e)}'})
    return JsonResponse({'success': True})

@csrf_exempt
@login_required
@require_POST
def rerun_ai_profile_generation(request, vacancy_id):
    """
    Генерирует профили должности для всех грейдов с помощью Gemini API, сохраняет в базе и возвращает JSON с данными по каждому грейду.
    """
    from .models import Vacancy, PositionProfileGrade, Grade, Parameter, ParameterDescription
    vacancy = get_object_or_404(Vacancy, pk=vacancy_id)
    profile = getattr(vacancy, 'profile', None)
    if not profile:
        return JsonResponse({'success': False, 'error': 'Профиль не найден'})
    profile_grades = list(profile.grade_profiles.select_related('grade').order_by('grade__order'))
    if not profile_grades:
        return JsonResponse({'success': False, 'error': 'Нет грейдов для профиля'})
    # Собираем параметры по грейдам
    grades = Grade.objects.all().order_by('order')
    parameters_by_grade = {}
    for grade in grades:
        params = ParameterDescription.objects.filter(grade=grade, parameter__position=vacancy.position)
        parameters_by_grade[grade.id] = [p.description for p in params if p.description]
    # Последовательная генерация
    prev_profile = None
    result_data = []
    for idx, pg in enumerate(profile_grades):
        grade = pg.grade
        params = parameters_by_grade.get(grade.id, [])
        # Формируем промпт
        prompt = f"""
        Сгенерируй профиль должности для грейда "{grade.name}" по специализации "{vacancy.position.name}".
        Параметры для этого грейда:
        {chr(10).join(params) if params else 'Нет параметров'}
        """
        if prev_profile:
            prompt += f"\nУчитывай, что для предыдущего грейда профиль был такой:\nОписание: {prev_profile.general_description}\nHard skills: {prev_profile.hard_skills}\nSoft/meta skills: {prev_profile.soft_meta_skills}\nПояснения: {prev_profile.notes}"
        prompt += "\nОбязательно сгенерируй не менее 5 hard skills и не менее 5 soft/meta skills, даже если они частично повторяются. Не оставляй эти поля пустыми. Ответ верни только в формате JSON с ключами: general_description, hard_skills (список), soft_meta_skills (список), notes. Без пояснений, без текста до и после, только JSON."
        # Запрос к Gemini
        api_key = GEMINI_API_KEY
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + api_key
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=60)
            try:
                resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                print('Gemini API error:', resp.status_code, resp.text)
                return JsonResponse({'success': False, 'error': f'Gemini API error: {str(e)}', 'response': resp.text})
            result = resp.json()
            print('Gemini raw response:', repr(result))
            if not result.get('candidates'):
                return JsonResponse({'success': False, 'error': f'Gemini не вернул кандидатов: {result}'})
            text = result['candidates'][0]['content']['parts'][0].get('text', '')
            if not text.strip():
                return JsonResponse({'success': False, 'error': f'Gemini вернул пустой текст: {repr(text)}'})
            # Удаляем markdown-обёртку, если есть
            text = text.strip()
            if text.startswith('```json'):
                text = text[len('```json'):].strip()
            if text.startswith('```'):
                text = text[len('```'):].strip()
            if text.endswith('```'):
                text = text[:-3].strip()
            import json as pyjson
            try:
                parsed = pyjson.loads(text)
            except Exception as e:
                print('Gemini ответ не JSON:', repr(text))
                return JsonResponse({'success': False, 'error': f'Ответ Gemini не JSON: {text[:200]}...'})
            pg.general_description = parsed.get('general_description', '')
            pg.hard_skills = '\n'.join(parsed.get('hard_skills', []))
            pg.soft_meta_skills = '\n'.join(parsed.get('soft_meta_skills', []))
            pg.notes = parsed.get('notes', '')
            pg.save()
            prev_profile = pg
            result_data.append({
                'grade_id': grade.id,
                'grade_name': grade.name,
                'general_description': pg.general_description,
                'hard_skills': parsed.get('hard_skills', []),
                'soft_meta_skills': parsed.get('soft_meta_skills', []),
                'notes': pg.notes
            })
        except Exception as e:
            print('Ошибка генерации Gemini:', str(e))
            return JsonResponse({'success': False, 'error': f'Ошибка генерации для грейда {grade.name}: {str(e)}'})
    return JsonResponse({'success': True, 'grades': result_data})