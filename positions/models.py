from django.db import models

# Create your models here.

class Grade(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название грейда')
    positions = models.TextField(verbose_name='Должности', blank=True)
    order = models.IntegerField(verbose_name='Порядок', default=0)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Грейд'
        verbose_name_plural = 'Грейды'
        ordering = ['order']

class Position(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Название специализации')
    
    def __str__(self):
        return self.name
    
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
