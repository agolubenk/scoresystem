from django import forms
from .models import Grade

class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ['name', 'positions', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'positions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        } 