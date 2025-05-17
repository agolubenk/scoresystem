from django.contrib import admin
from .models import Grade, Position, PositionGrade, Parameter, ParameterDescription, InterviewQuestion, Candidate, CandidateFile, CandidateTask, CandidateChangeHistory, CandidateComment, Vacancy, PositionProfile, PositionProfileGrade

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'positions')
    list_editable = ('order',)
    ordering = ('order',)

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(PositionGrade)
class PositionGradeAdmin(admin.ModelAdmin):
    list_display = ('position', 'grade', 'confirmation_points', 'promotion_points')
    list_filter = ('grade', 'position')
    search_fields = ('position__name',)
    ordering = ('position__name', 'grade__name')

@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ('name', 'position', 'created_at', 'updated_at')
    list_filter = ('position',)
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(ParameterDescription)
class ParameterDescriptionAdmin(admin.ModelAdmin):
    list_display = ('parameter', 'grade', 'description')
    list_filter = ('grade', 'parameter')
    search_fields = ('parameter__name', 'description')
    ordering = ('parameter__name', 'grade__name')

@admin.register(InterviewQuestion)
class InterviewQuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'position', 'question_type', 'test_type', 'order', 'is_active')
    list_filter = ('position', 'question_type', 'test_type', 'is_active')
    search_fields = ('text',)
    list_editable = ('order', 'is_active')
    ordering = ('position__name', 'order')
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'test_type' in form.base_fields:
            form.base_fields['test_type'].required = False
        return form

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'desired_position', 'created_at')
    list_filter = ('desired_position', 'created_at')
    search_fields = ('full_name', 'email', 'phone', 'desired_position__name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Основная информация', {
            'fields': ('full_name', 'email', 'phone', 'telegram')
        }),
        ('Должность', {
            'fields': ('desired_position',)
        }),
        ('Документы', {
            'fields': ('resume',)
        }),
        ('Дополнительно', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['desired_position'].queryset = Position.objects.filter(is_active=True)
        return form

@admin.register(CandidateTask)
class CandidateTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'candidate', 'due_date', 'is_completed', 'created_at')
    list_filter = ('is_completed', 'due_date', 'candidate')
    search_fields = ('title', 'description', 'candidate__full_name')

@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ('name', 'position', 'created_at', 'updated_at')
    list_filter = ('position',)
    search_fields = ('name', 'description')
    ordering = ('-created_at',)

@admin.register(PositionProfile)
class PositionProfileAdmin(admin.ModelAdmin):
    list_display = ('vacancy', 'position', 'created_at', 'updated_at')
    list_filter = ('vacancy__position',)
    search_fields = ('profile_text', 'vacancy__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    def position(self, obj):
        return obj.vacancy.position
    position.short_description = 'Специализация'

@admin.register(PositionProfileGrade)
class PositionProfileGradeAdmin(admin.ModelAdmin):
    list_display = ('profile', 'grade', 'position', 'salary_range', 'supervisor')
    list_filter = ('grade', 'profile__vacancy__position')
    search_fields = ('profile__vacancy__name', 'general_description', 'hard_skills', 'soft_meta_skills', 'supervisor')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('grade__order',)
    
    def position(self, obj):
        return obj.profile.vacancy.position
    position.short_description = 'Специализация'
    
    def salary_range(self, obj):
        if obj.salary_min and obj.salary_max:
            return f"{obj.salary_min} - {obj.salary_max}"
        elif obj.salary_min:
            return f"от {obj.salary_min}"
        elif obj.salary_max:
            return f"до {obj.salary_max}"
        return "—"
    salary_range.short_description = 'Зарплата'
