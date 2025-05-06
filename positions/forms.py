from django import forms
from .models import Grade, Candidate, Position

class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ['name', 'positions', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'positions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class CandidateForm(forms.ModelForm):
    telegram = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'username',
            'data-prefix': '@'
        })
    )

    class Meta:
        model = Candidate
        fields = ['full_name', 'email', 'phone', 'telegram', 'desired_position', 'resume', 'notes']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'desired_position': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'resume': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf',
                'data-bs-toggle': 'tooltip',
                'title': 'Загрузите резюме в формате PDF'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['desired_position'].queryset = Position.objects.filter(is_active=True)
        self.fields['desired_position'].empty_label = "Выберите должность"
        
        # Если есть значение telegram, убираем @ из начала
        if self.instance and self.instance.telegram:
            self.initial['telegram'] = self.instance.get_telegram_username()

    def clean_telegram(self):
        telegram = self.cleaned_data.get('telegram')
        if telegram:
            # Убираем @ если он есть в начале
            telegram = telegram.lstrip('@')
            # Если это ссылка, извлекаем username
            if 't.me/' in telegram:
                telegram = telegram.split('t.me/')[-1]
        return telegram

    def clean_resume(self):
        resume = self.cleaned_data.get('resume')
        if resume and not resume.name.lower().endswith('.pdf'):
            raise forms.ValidationError('Загрузите файл в формате PDF.')
        return resume 