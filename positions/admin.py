from django.contrib import admin
from .models import Grade, Position, PositionGrade, Parameter, ParameterDescription, InterviewQuestion

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
