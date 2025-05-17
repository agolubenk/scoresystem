from django.db import models
from django.db.models import Sum
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from django.contrib.auth import get_user_model

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
        """Переопределяем метод save для автоматического создания матрицы, вакансии и профиля"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Создаем матрицу пересчета при создании новой специализации
            ScoreMatrix.objects.create(
                position=self,
                name=self.name,
                description=f'Матрица пересчета баллов для специализации {self.name}'
            )
            
            # Создаем вакансию
            vacancy = Vacancy.objects.create(
                name=f'Вакансия {self.name}',
                position=self,
                description=f'Описание вакансии для специализации {self.name}'
            )
            
            # Создаем профиль должности
            PositionProfile.objects.create(
                vacancy=vacancy,
                profile_text=f'Профиль должности для специализации {self.name}'
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

class Candidate(models.Model):
    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    phone = models.CharField(max_length=30, blank=True, null=True, verbose_name="Телефон")
    telegram = models.CharField(max_length=100, blank=True, null=True, verbose_name="Telegram (ссылка)")
    desired_position = models.ForeignKey('Position', on_delete=models.PROTECT, null=True, blank=True, verbose_name="Желаемая должность")
    resume = models.FileField(upload_to='resumes/', blank=True, null=True, verbose_name="Резюме (PDF)")
    notes = models.TextField(blank=True, verbose_name="Заметки")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_telegram_username(self):
        if not self.telegram:
            return None
        # Убираем @ если он есть в начале
        username = self.telegram.lstrip('@')
        # Если это ссылка, извлекаем username
        if 't.me/' in username:
            username = username.split('t.me/')[-1]
        return username

    def get_telegram_link(self):
        username = self.get_telegram_username()
        if not username:
            return None
        return f"https://t.me/{username}"

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Кандидат"
        verbose_name_plural = "Кандидаты"
        ordering = ['full_name']

class TestAnswer(models.Model):
    question = models.ForeignKey(InterviewQuestion, on_delete=models.CASCADE, related_name='answers', verbose_name='Вопрос')
    text = models.TextField(verbose_name='Текст ответа')
    is_correct = models.BooleanField(default=False, verbose_name='Правильный ответ')
    order = models.IntegerField(default=0, verbose_name='Порядок')
    
    class Meta:
        verbose_name = 'Вариант ответа'
        verbose_name_plural = 'Варианты ответов'
        ordering = ['question', 'order']
    
    def __str__(self):
        return f"{self.question.text[:50]} - {self.text[:50]}"

class CandidateFile(models.Model):
    candidate = models.ForeignKey('Candidate', on_delete=models.CASCADE, related_name='files', verbose_name='Кандидат')
    file = models.FileField(upload_to='candidate_files/', verbose_name='Файл')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Загружено')
    
    def __str__(self):
        return self.file.name.split('/')[-1]

class CandidateTask(models.Model):
    candidate = models.ForeignKey('Candidate', on_delete=models.CASCADE, related_name='tasks', verbose_name='Кандидат')
    title = models.CharField(max_length=255, verbose_name='Название задачи')
    description = models.TextField(blank=True, verbose_name='Описание')
    due_date = models.DateField(null=True, blank=True, verbose_name='Дедлайн')
    is_completed = models.BooleanField(default=False, verbose_name='Выполнено')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Задача по кандидату'
        verbose_name_plural = 'Задачи по кандидату'

class CandidateChangeHistory(models.Model):
    candidate = models.ForeignKey('Candidate', on_delete=models.CASCADE, related_name='change_history')
    field = models.CharField(max_length=100)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.candidate.full_name}: {self.field} ({self.changed_at})"

class CandidateComment(models.Model):
    candidate = models.ForeignKey('Candidate', on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Автор')
    text = models.TextField(verbose_name='Комментарий')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Комментарий от {self.author} ({self.created_at})"

class Vacancy(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название вакансии')
    position = models.ForeignKey('Position', on_delete=models.CASCADE, verbose_name='Специализация')
    description = models.TextField(verbose_name='Описание вакансии', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Вакансия'
        verbose_name_plural = 'Вакансии'
        ordering = ['-created_at']

class VacancyGrade(models.Model):
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name='grades', verbose_name='Вакансия')
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, verbose_name='Грейд')
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Мин. ЗП')
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Макс. ЗП')
    requirements = models.TextField(verbose_name='Требования', blank=True)
    responsibilities = models.TextField(verbose_name='Обязанности', blank=True)
    wishes = models.TextField('Пожелания к кандидату', blank=True)
    work_conditions = models.TextField('Условия труда', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.vacancy.name} - {self.grade.name}"

    class Meta:
        verbose_name = 'Грейд вакансии'
        verbose_name_plural = 'Грейды вакансий'
        unique_together = ['vacancy', 'grade']
        ordering = ['grade__order']

class PositionProfile(models.Model):
    vacancy = models.OneToOneField(Vacancy, on_delete=models.CASCADE, related_name='profile', verbose_name='Вакансия')
    profile_text = models.TextField(verbose_name='Профиль должности')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Профиль для {self.vacancy.name}'

    class Meta:
        verbose_name = 'Профиль должности'
        verbose_name_plural = 'Профили должностей'
        ordering = ['-created_at']

class PositionProfileGrade(models.Model):
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name='profile_grades', verbose_name='Вакансия')
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, verbose_name='Грейд')
    profile = models.ForeignKey(PositionProfile, on_delete=models.CASCADE, related_name='grade_profiles', verbose_name='Профиль должности')
    general_description = models.TextField('Общее описание', blank=True)
    hard_skills = models.TextField('Hard skills', blank=True)
    hard_requirements = models.TextField('Требования к hard skills', blank=True)
    hard_level = models.TextField('Уровень владения hard skills', blank=True)
    soft_meta_skills = models.TextField('Soft & meta skills', blank=True)
    notes = models.TextField('Пояснения', blank=True)
    salary_min = models.DecimalField('Зарплата (от)', max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField('Зарплата (до)', max_digits=10, decimal_places=2, null=True, blank=True)
    supervisor = models.CharField('Руководитель', max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.profile} — {self.grade.name}'

    class Meta:
        verbose_name = 'Профиль по грейду'
        verbose_name_plural = 'Профили по грейдам'
        unique_together = ['vacancy', 'grade', 'profile']
        ordering = ['grade__order']
