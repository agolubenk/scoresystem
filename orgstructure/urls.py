from django.urls import path
from . import views

app_name = 'orgstructure'

urlpatterns = [
    path('', views.orgstructure_tree, name='org_tree'),
    path('department/add/', views.department_create, name='department_add'),
    path('department/<int:pk>/edit/', views.department_edit, name='department_edit'),
    path('department/<int:pk>/delete/', views.DepartmentDeleteView.as_view(), name='department_delete'),
    path('staff/add/', views.staff_create, name='staff_add'),
    path('staff/<int:pk>/edit/', views.staff_edit, name='staff_edit'),
    path('staff/<int:pk>/delete/', views.StaffMemberDeleteView.as_view(), name='staff_delete'),
    path('svg/', views.orgstructure_tree_svg, name='org_tree_svg'),
    path('orgchart/', views.orgstructure_tree_orgchart, name='org_tree_orgchart'),
    path('d3js/', views.orgstructure_tree_d3js, name='org_tree_d3js'),
    path('department-types/', views.department_type_list, name='department_type_list'),
    path('department-types/create/', views.department_type_create, name='department_type_create'),
    path('department-types/<int:pk>/edit/', views.department_type_edit, name='department_type_edit'),
    path('department-types/<int:pk>/delete/', views.department_type_delete, name='department_type_delete'),
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/<int:pk>/', views.staff_detail, name='staff_detail'),
] 