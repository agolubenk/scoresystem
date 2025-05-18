from django.contrib import admin
from .models import Department, StaffMember

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    search_fields = ('name',)
    list_filter = ('parent',)

@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'position', 'department', 'email', 'phone', 'hired_at', 'is_active')
    search_fields = ('full_name', 'position', 'email', 'phone')
    list_filter = ('department', 'is_active')
