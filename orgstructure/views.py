from django.shortcuts import render, get_object_or_404, redirect
from .models import Department, StaffMember, DepartmentType
from django.urls import reverse, reverse_lazy
from django import forms
from django.views.generic import DeleteView
from django.contrib import messages
from positions.models import Candidate
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string

# Create your views here.

# Формы
class DepartmentForm(forms.ModelForm):
    type = forms.ModelChoiceField(
        queryset=DepartmentType.objects.all(),
        required=True,
        label='Тип отдела',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    class Meta:
        model = Department
        fields = ['name', 'parent', 'type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
        }

class StaffMemberForm(forms.ModelForm):
    candidate = forms.ModelChoiceField(
        queryset=Candidate.objects.filter(staff_members__isnull=True),
        required=False,
        label='Кандидат',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Выберите кандидата для трудоустройства'
    )

    class Meta:
        model = StaffMember
        fields = ['candidate', 'position', 'department', 'email', 'phone', 'hired_at', 'is_active']
        widgets = {
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'hired_at': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.candidate:
            self.fields['candidate'].initial = self.instance.candidate
            self.fields['candidate'].queryset = Candidate.objects.filter(
                staff_members__isnull=True
            ) | Candidate.objects.filter(pk=self.instance.candidate.pk)

    def save(self, commit=True):
        instance = super().save(commit=False)
        candidate = self.cleaned_data.get('candidate')
        if candidate:
            instance.candidate = candidate
            instance.position = candidate.desired_position
            instance.email = candidate.email
            instance.phone = candidate.phone
        if commit:
            instance.save()
        return instance

# Древовидный вывод оргструктуры
def orgstructure_tree(request):
    departments = Department.objects.filter(parent__isnull=True)
    staff = StaffMember.objects.all()
    add_form = DepartmentForm()
    total_staff_count = StaffMember.objects.count()
    return render(request, 'orgstructure/org_tree.html', {
        'departments': departments,
        'staff': staff,
        'add_form': add_form,
        'total_staff_count': total_staff_count,
    })

def orgstructure_tree_svg(request):
    departments = Department.objects.filter(parent__isnull=True)
    staff = StaffMember.objects.all()

    # Параметры для отрисовки
    box_w = 200
    box_h = 50
    h_gap = 80
    v_gap = 100
    circle_r = 16
    circle_y_offset = 32
    circle_x_step = 40

    # Рекурсивная функция для координат
    def set_svg_coords(dep, x, y):
        dep.svg_x = x
        dep.svg_y = y
        dep.svg_center_x = x + box_w // 2
        dep.svg_bottom_y = y + box_h
        dep_staff = dep.staff.all()
        n = dep_staff.count()
        center_x = dep.svg_center_x
        base_y = y + box_h + circle_y_offset
        coords = []
        for idx, s in enumerate(dep_staff):
            offset = (idx - (n - 1) / 2) * circle_x_step
            coords.append({
                'x': center_x + offset,
                'y': base_y,
                'full_name': s.full_name,
                'position': s.position,
                'initials': (s.full_name[:1] + (s.full_name.split(' ')[1][:1] if len(s.full_name.split(' ')) > 1 else '')),
            })
        dep.staff_coords = coords
        # Рекурсивно для детей
        children = dep.children.all()
        n_children = children.count()
        for idx, child in enumerate(children):
            child_x = x + (box_w + h_gap) * (idx - (n_children - 1) / 2)
            child_y = y + box_h + v_gap
            set_svg_coords(child, child_x, child_y)

    for idx, dep in enumerate(departments):
        x = 80 + idx * (box_w + h_gap)
        y = 60
        set_svg_coords(dep, x, y)

    return render(request, 'orgstructure/org_tree_svg.html', {
        'departments': departments,
        'staff': staff,
        'box_w': box_w,
        'box_h': box_h,
        'h_gap': h_gap,
        'v_gap': v_gap,
        'circle_r': circle_r,
    })

# CRUD для отделов

def department_create(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            return redirect('orgstructure:org_tree')
    else:
        form = DepartmentForm()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('orgstructure/department_form_inner.html', {'form': form}, request=request)
        return JsonResponse({'html': html})
    return render(request, 'orgstructure/department_form.html', {'form': form, 'action': 'add'})

def department_edit(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            return redirect('orgstructure:org_tree')
    else:
        form = DepartmentForm(instance=department)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('orgstructure/department_form_inner.html', {'form': form}, request=request)
        return JsonResponse({'html': html})
    return render(request, 'orgstructure/department_form.html', {'form': form, 'action': 'edit', 'department': department})

def department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        department.delete()
        return redirect('orgstructure:org_tree')
    return render(request, 'orgstructure/department_confirm_delete.html', {'department': department})

# CRUD для сотрудников

def staff_create(request):
    candidates = Candidate.objects.filter(staff_members__isnull=True)
    candidates_data = [
        {
            'id': c.id,
            'full_name': c.full_name,
            'email': c.email,
            'phone': c.phone,
            'desired_position': str(c.desired_position) if c.desired_position else '',
        } for c in candidates
    ]
    if request.method == 'POST':
        form = StaffMemberForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('orgstructure:org_tree')
    else:
        form = StaffMemberForm()
    return render(request, 'orgstructure/staff_form.html', {
        'form': form,
        'action': 'add',
        'candidates_json': json.dumps(candidates_data, ensure_ascii=False),
    })

def staff_edit(request, pk):
    staff = get_object_or_404(StaffMember, pk=pk)
    candidates = Candidate.objects.filter(staff_members__isnull=True) | Candidate.objects.filter(pk=staff.candidate_id)
    candidates_data = [
        {
            'id': c.id,
            'full_name': c.full_name,
            'email': c.email,
            'phone': c.phone,
            'desired_position': str(c.desired_position) if c.desired_position else '',
        } for c in candidates
    ]
    if request.method == 'POST':
        form = StaffMemberForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            return redirect('orgstructure:org_tree')
    else:
        form = StaffMemberForm(instance=staff)
    return render(request, 'orgstructure/staff_form.html', {
        'form': form,
        'action': 'edit',
        'staff': staff,
        'candidates_json': json.dumps(candidates_data, ensure_ascii=False),
    })

def staff_delete(request, pk):
    staff = get_object_or_404(StaffMember, pk=pk)
    if request.method == 'POST':
        staff.delete()
        return redirect('orgstructure:org_tree')
    return render(request, 'orgstructure/staff_confirm_delete.html', {'staff': staff})

class DepartmentDeleteView(DeleteView):
    model = Department
    template_name = 'orgstructure/confirm_delete.html'
    success_url = reverse_lazy('orgstructure:org_tree')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = reverse_lazy('orgstructure:org_tree')
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Отдел успешно удален')
        return super().delete(request, *args, **kwargs)

class StaffMemberDeleteView(DeleteView):
    model = StaffMember
    template_name = 'orgstructure/confirm_delete.html'
    success_url = reverse_lazy('orgstructure:staff_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = reverse_lazy('orgstructure:staff_list')
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Сотрудник успешно удален')
        return super().delete(request, *args, **kwargs)

def orgstructure_tree_orgchart(request):
    # Собираем данные для OrgChart JS
    departments = Department.objects.all()
    staff = StaffMember.objects.all()
    nodes = []
    # Сначала отделы
    for dep in departments:
        nodes.append({
            'id': f'dep_{dep.id}',
            'name': dep.name,
            'title': 'Отдел',
            'parent': f'dep_{dep.parent_id}' if dep.parent_id else '',
            'type': 'department',
        })
    # Затем сотрудники
    for s in staff:
        nodes.append({
            'id': f'staff_{s.id}',
            'name': s.full_name or 'Без имени',
            'title': s.position,
            'parent': f'dep_{s.department_id}',
            'type': 'staff',
        })
    return render(request, 'orgstructure/org_tree_orgchart.html', {
        'orgchart_data': json.dumps(nodes, ensure_ascii=False),
    })

def orgstructure_tree_d3js(request):
    # Рекурсивно строим вложенную структуру для d3.js (только отделы)
    def build_tree(dep):
        node = {
            'name': dep.name,
            'type': 'department',
            'color': dep.type.color if dep.type else '#2563eb',
            'children': []
        }
        # Рекурсивно добавляем подотделы
        for child in dep.children.all():
            node['children'].append(build_tree(child))
        return node

    roots = Department.objects.filter(parent__isnull=True)
    tree = [build_tree(dep) for dep in roots]
    return render(request, 'orgstructure/org_tree_d3js.html', {
        'd3_data': json.dumps(tree[0] if len(tree) == 1 else {'name': 'Оргструктура', 'children': tree}, ensure_ascii=False),
    })

# CRUD для типов отделов (DepartmentType)
def department_type_list(request):
    # Автосоздание базовых типов, если их нет
    base_types = [
        ("Блок", "#2563eb"),
        ("Группа", "#059669"),
        ("Отдел", "#f59e42"),
        ("Управление", "#a21caf"),
        ("Департамент", "#e11d48"),
    ]
    for name, color in base_types:
        DepartmentType.objects.get_or_create(name=name, defaults={"color": color})
    types = DepartmentType.objects.all().values('id', 'name', 'color')
    return JsonResponse({'types': list(types)})

@require_POST
def department_type_create(request):
    name = request.POST.get('name')
    color = request.POST.get('color', '#2563eb')
    if not name:
        return JsonResponse({'error': 'Название обязательно'}, status=400)
    dt = DepartmentType.objects.create(name=name, color=color)
    return JsonResponse({'id': dt.id, 'name': dt.name, 'color': dt.color})

@require_POST
def department_type_edit(request, pk):
    dt = get_object_or_404(DepartmentType, pk=pk)
    name = request.POST.get('name')
    color = request.POST.get('color', '#2563eb')
    if not name:
        return JsonResponse({'error': 'Название обязательно'}, status=400)
    dt.name = name
    dt.color = color
    dt.save()
    return JsonResponse({'id': dt.id, 'name': dt.name, 'color': dt.color})

@require_POST
def department_type_delete(request, pk):
    dt = get_object_or_404(DepartmentType, pk=pk)
    dt.delete()
    return JsonResponse({'success': True})
