from django.db import models

# Create your models here.

# Новая модель для типов отделов
class DepartmentType(models.Model):
    name = models.CharField(max_length=64, unique=True, verbose_name='Тип отдела')
    color = models.CharField(max_length=7, default='#2563eb', verbose_name='Цвет (HEX)')

    class Meta:
        verbose_name = 'Тип отдела'
        verbose_name_plural = 'Типы отделов'

    def __str__(self):
        return self.name

class Department(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название отдела')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children', verbose_name='Вышестоящий отдел')
    type = models.ForeignKey(DepartmentType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Тип отдела')

    class Meta:
        verbose_name = 'Отдел'
        verbose_name_plural = 'Отделы'

    def __str__(self):
        return self.name

class StaffMember(models.Model):
    full_name = models.CharField(max_length=255, verbose_name='ФИО')
    position = models.CharField(max_length=255, verbose_name='Должность')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='staff', verbose_name='Отдел')
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name='Телефон')
    hired_at = models.DateField(verbose_name='Дата найма')
    is_active = models.BooleanField(default=True, verbose_name='Работает в компании')
    candidate = models.ForeignKey('positions.Candidate', on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_members', verbose_name='Кандидат (если был)')

    class Meta:
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'

    def __str__(self):
        return self.full_name
