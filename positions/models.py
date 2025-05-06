from django.db import models
from django.db.models import Sum
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse

# Create your models here.

class Grade(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название грейда')
    positions = models.TextField(verbose_name='Должности', blank=True)
    order = models.IntegerField(verbose_name='Порядок', default=0)
    min_score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Минимальный балл', default=0)
    max_score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Максимальный балл', default=100)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Грейд'
        verbose_name_plural = 'Грейды'
        ordering = ['order']

class Position(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Название специализации')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Переопределяем метод save для автоматического создания матрицы"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Создаем матрицу пересчета при создании новой специализации
            ScoreMatrix.objects.create(
                position=self,
                name=self.name,
                description=f'Матрица пересчета баллов для специализации {self.name}'
            )
    
    class Meta:
        verbose_name = 'Специализация'
        verbose_name_plural = 'Специализации'
        ordering = ['name']

class Parameter(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Название параметра")
    position = models.ForeignKey(Position, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Специализация")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Параметр"
        verbose_name_plural = "Параметры"
        ordering = ['name']

class ParameterDescription(models.Model):
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE, related_name='descriptions', verbose_name="Параметр")
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='parameter_descriptions', verbose_name="Грейд")
    description = models.TextField(verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Описание параметра"
        verbose_name_plural = "Описания параметров"
        unique_together = ['parameter', 'grade']
        ordering = ['parameter__name', 'grade__name']

    def __str__(self):
        return f"{self.parameter.name} - {self.grade.name}"

class PositionGrade(models.Model):
    position = models.ForeignKey(Position, on_delete=models.CASCADE, verbose_name='Специализация')
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, verbose_name='Грейд')
    confirmation_points = models.IntegerField(verbose_name='Подтверждающие баллы')
    promotion_points = models.IntegerField(verbose_name='Повышающие баллы')
    
    def __str__(self):
        return f"{self.position.name} - {self.grade.name}"
    
    class Meta:
        verbose_name = 'Специализация в грейде'
        verbose_name_plural = 'Специализации в грейдах'
        unique_together = ['position', 'grade']
        ordering = ['position__name', 'grade__name']

class InterviewQuestion(models.Model):
    QUESTION_TYPES = [
        ('question', 'Вопрос'),
        ('test', 'Тестовое'),
    ]

    TEST_TYPES = [
        ('single_choice', 'Один ответ'),
        ('multiple_choice', 'Множественный ответ'),
        ('open_ended', 'Открытый вопрос'),
        ('drag_drop', 'Карточки (drag&drop)'),
    ]

    text = models.TextField(verbose_name='Текст вопроса')
    position = models.ForeignKey(Position, on_delete=models.CASCADE, verbose_name='Специализация')
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        verbose_name='Тип вопроса',
        default='question'
    )
    test_type = models.CharField(
        max_length=20,
        choices=TEST_TYPES,
        verbose_name='Тип тестового',
        null=True,
        blank=True
    )
    order = models.IntegerField(verbose_name='Порядок', default=0)
    is_active = models.BooleanField(verbose_name='Активен', default=True)
    created_at = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name='Дата обновления', auto_now=True)

    def __str__(self):
        question_type_display = self.get_question_type_display()
        if self.question_type == 'test':
            return f"{self.text[:50]}... ({question_type_display} - {self.get_test_type_display()})"
        return f"{self.text[:50]}... ({question_type_display})"
    
    class Meta:
        verbose_name = 'Вопрос интервью'
        verbose_name_plural = 'Вопросы интервью'
        ordering = ['position__name', 'order']
        unique_together = ['text', 'position']

class ScoreMatrix(models.Model):
    """Матрица пересчета баллов"""
    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='score_matrices')
    name = models.CharField(max_length=255, verbose_name='Название матрицы')
    description = models.TextField(blank=True, verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Матрица пересчета баллов'
        verbose_name_plural = 'Матрицы пересчета баллов'
        ordering = ['-created_at']
        unique_together = ['position', 'name']

    def __str__(self):
        return f"{self.name} ({self.position.name})"

    def get_matrix_data(self):
        """Получить данные матрицы в виде словаря"""
        parameters = Parameter.objects.filter(position=self.position)
        questions = InterviewQuestion.objects.filter(position=self.position)
        
        # Получаем все ячейки матрицы
        cells = self.cells.all()
        cell_dict = {}
        for cell in cells:
            if cell.parameter_id not in cell_dict:
                cell_dict[cell.parameter_id] = {}
            cell_dict[cell.parameter_id][cell.question_id] = float(cell.score)
        
        # Получаем суммы
        sums = self.sums.all()
        row_sums = {sum.parameter_id: float(sum.sum_value) for sum in sums if sum.is_row_sum}
        col_sums = {sum.question_id: float(sum.sum_value) for sum in sums if not sum.is_row_sum}
        
        return {
            'parameters': list(parameters.values('id', 'name')),
            'questions': list(questions.values('id', 'text')),
            'cells': cell_dict,
            'row_sums': row_sums,
            'col_sums': col_sums
        }

    def update_sums(self):
        """Обновить суммы по строкам и столбцам"""
        # Удаляем старые суммы
        self.sums.all().delete()
        
        # Обновляем суммы по строкам (параметрам)
        row_sums = self.cells.values('parameter').annotate(
            sum_value=Sum('score')
        )
        for row_sum in row_sums:
            ScoreMatrixSum.objects.create(
                matrix=self,
                parameter_id=row_sum['parameter'],
                sum_value=row_sum['sum_value'],
                is_row_sum=True
            )
        
        # Обновляем суммы по столбцам (вопросам)
        col_sums = self.cells.values('question').annotate(
            sum_value=Sum('score')
        )
        for col_sum in col_sums:
            ScoreMatrixSum.objects.create(
                matrix=self,
                question_id=col_sum['question'],
                sum_value=col_sum['sum_value'],
                is_row_sum=False
            )

    def update_cell(self, parameter_id, question_id, score):
        """Обновить значение ячейки"""
        cell, created = ScoreMatrixCell.objects.get_or_create(
            matrix=self,
            parameter_id=parameter_id,
            question_id=question_id,
            defaults={'score': score}
        )
        if not created:
            cell.score = score
            cell.save()
        return cell

class ScoreMatrixCell(models.Model):
    """Ячейка матрицы пересчета баллов"""
    matrix = models.ForeignKey(ScoreMatrix, on_delete=models.CASCADE, related_name='cells')
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE, verbose_name='Параметр')
    question = models.ForeignKey(InterviewQuestion, on_delete=models.CASCADE, verbose_name='Вопрос')
    score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Балл')

    class Meta:
        verbose_name = 'Ячейка матрицы'
        verbose_name_plural = 'Ячейки матрицы'
        unique_together = ['matrix', 'parameter', 'question']

    def __str__(self):
        return f"{self.parameter.name} - {self.question.text[:50]}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.matrix.update_sums()

class ScoreMatrixSum(models.Model):
    """Суммы по строкам и столбцам матрицы"""
    matrix = models.ForeignKey(ScoreMatrix, on_delete=models.CASCADE, related_name='sums')
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Параметр')
    question = models.ForeignKey(InterviewQuestion, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Вопрос')
    sum_value = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='Сумма')
    is_row_sum = models.BooleanField(default=True, verbose_name='Сумма по строке')

    class Meta:
        verbose_name = 'Сумма матрицы'
        verbose_name_plural = 'Суммы матрицы'
        unique_together = ['matrix', 'parameter', 'question', 'is_row_sum']

    def __str__(self):
        if self.is_row_sum:
            return f"Сумма по параметру {self.parameter.name}"
        return f"Сумма по вопросу {self.question.text[:50]}"

class Interview(models.Model):
    position = models.ForeignKey(Position, on_delete=models.CASCADE, verbose_name="Специализация")
    candidate_name = models.CharField(max_length=255, verbose_name="ФИО кандидата")
    expected_grade = models.ForeignKey(Grade, on_delete=models.SET_NULL, null=True, related_name='expected_interviews', verbose_name="Ожидаемый грейд")
    expected_salary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ожидаемая ЗП")
    current_grade = models.ForeignKey(Grade, on_delete=models.SET_NULL, null=True, blank=True, related_name='current_interviews', verbose_name="Текущий грейд")
    general_notes = models.TextField(blank=True, verbose_name="Общие заметки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        verbose_name = "Интервью"
        verbose_name_plural = "Интервью"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Интервью {self.candidate_name} - {self.position.name}"
        
    def get_absolute_url(self):
        return reverse('positions:interview_conduct', kwargs={'pk': self.pk})

class InterviewAnswer(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='answers', verbose_name="Интервью")
    question = models.ForeignKey(InterviewQuestion, on_delete=models.CASCADE, verbose_name="Вопрос")
    score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)], verbose_name="Балл")
    notes = models.TextField(blank=True, verbose_name="Заметки")
    
    class Meta:
        verbose_name = "Ответ на вопрос"
        verbose_name_plural = "Ответы на вопросы"
        unique_together = ['interview', 'question']
    
    def __str__(self):
        return f"Ответ {self.interview.candidate_name} на вопрос {self.question.text}"

class InterviewResult(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='results', verbose_name="Интервью")
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE, verbose_name="Параметр")
    score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Балл")
    
    class Meta:
        verbose_name = "Результат по параметру"
        verbose_name_plural = "Результаты по параметрам"
        unique_together = ['interview', 'parameter']
    
    def __str__(self):
        return f"Результат {self.interview.candidate_name} по параметру {self.parameter.name}"
