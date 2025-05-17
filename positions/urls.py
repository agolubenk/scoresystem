from django.urls import path
from . import views
from .views import add_candidate_comment, edit_candidate_comment

app_name = 'positions'

urlpatterns = [
    path('', views.index, name='index'),
    path('grades/', views.GradeListView.as_view(), name='grades'),
    path('grades/<int:pk>/', views.GradeListView.as_view(), name='grade_detail'),
    path('positions/', views.positions_list, name='positions'),
    path('positions/create/', views.create_position, name='create_position'),
    path('positions/<int:pk>/update/', views.update_position_by_id, name='update_position_by_id'),
    path('positions/delete/<str:position_name>/', views.delete_position, name='delete_position'),
    path('positions/update/', views.update_position_by_name, name='update_position_by_name'),
    path('parameters/', views.parameters, name='parameters'),
    path('parameters/create/', views.create_parameter, name='create_parameter'),
    path('parameters/<int:parameter_id>/update/', views.update_parameter, name='update_parameter'),
    path('parameters/<int:parameter_id>/delete/', views.delete_parameter, name='delete_parameter'),
    path('parameters/descriptions/create/', views.create_parameter_description, name='create_parameter_description'),
    path('parameters/descriptions/<int:description_id>/update/', views.update_parameter_description, name='update_parameter_description'),
    path('parameters/descriptions/<int:description_id>/delete/', views.delete_parameter_description, name='delete_parameter_description'),
    path('parameters/export_excel/', views.export_parameters_excel, name='export_parameters_excel'),
    path('parameters/import_excel/', views.import_parameters_excel, name='import_parameters_excel'),
    
    # URLs для вопросов интервью
    path('questions/', views.questions_list, name='questions'),
    path('questions/create/', views.create_question, name='create_question'),
    path('questions/<int:question_id>/update/', views.update_question, name='update_question'),
    path('questions/<int:question_id>/delete/', views.delete_question, name='delete_question'),
    path('questions/<int:question_id>/update_test_template/', views.update_test_template, name='update_test_template'),
    
    # URLs для матриц пересчета баллов
    path('score_matrices/', views.score_matrices, name='score_matrices'),
    path('score_matrices/create/', views.create_score_matrix, name='create_score_matrix'),
    path('score_matrices/<int:matrix_id>/edit/', views.edit_score_matrix, name='edit_score_matrix'),
    path('score_matrices/<int:matrix_id>/delete/', views.delete_score_matrix, name='delete_score_matrix'),
    path('score_matrices/<int:matrix_id>/toggle_active/', views.toggle_matrix_active, name='toggle_matrix_active'),
    path('score_matrices/<int:matrix_id>/download/', views.download_score_matrix, name='download_score_matrix'),
    path('score_matrices/<int:matrix_id>/upload/', views.upload_score_matrix, name='upload_score_matrix'),
    
    # URLs для интервью
    path('interview/create/', views.InterviewCreateView.as_view(), name='interview_create'),
    path('interview/<int:pk>/conduct/', views.InterviewConductView.as_view(), name='interview_conduct'),
    path('interview/<int:pk>/result/', views.InterviewResultView.as_view(), name='interview_result'),
    path('interview/<int:pk>/download/', views.download_interview_results, name='download_interview_results'),
    path('interview/<int:pk>/delete/', views.delete_interview, name='delete_interview'),
    path('interview/<int:pk>/rerun_ai/', views.rerun_ai_analysis, name='rerun_ai_analysis'),
    path('interview/', views.InterviewListView.as_view(), name='interview_list'),
    
    # URLs для кандидатов
    path('candidates/', views.CandidateListView.as_view(), name='candidate_list'),
    path('candidates/create/', views.CandidateCreateView.as_view(), name='candidate_create'),
    path('candidates/<int:pk>/', views.CandidateDetailView.as_view(), name='candidate_detail'),
    path('candidates/<int:pk>/edit/', views.CandidateUpdateView.as_view(), name='candidate_edit'),
    path('candidates/<int:pk>/delete/', views.CandidateDeleteView.as_view(), name='candidate_delete'),
    path('candidates/<int:pk>/resume/', views.candidate_resume_view, name='candidate_resume_view'),
    path('candidates/<int:pk>/files/upload/', views.candidate_files_upload, name='candidate_files_upload'),
    path('candidates/files/<int:file_id>/delete/', views.candidate_file_delete, name='candidate_file_delete'),
    path('candidates/<int:pk>/update/', views.candidate_update, name='candidate_update'),
    path('candidates/<int:pk>/tasks/', views.candidate_tasks, name='candidate_tasks'),
    path('candidates/<int:pk>/comments/add/', views.add_candidate_comment, name='add_candidate_comment'),
    path('candidates/comments/<int:comment_id>/edit/', views.edit_candidate_comment, name='edit_candidate_comment'),
    
    # URLs для вакансий и профилей
    path('vacancies/', views.vacancies_list, name='vacancies_list'),
    path('vacancies/create/', views.vacancy_create, name='vacancy_create'),
    path('vacancies/<int:pk>/', views.vacancy_detail, name='vacancy_detail'),
    path('vacancies/<int:pk>/edit/', views.vacancy_edit, name='vacancy_edit'),
    path('vacancies/<int:pk>/delete/', views.vacancy_delete, name='vacancy_delete'),
    path('vacancies/<int:vacancy_id>/profile/', views.profile_detail, name='profile_detail'),
    path('vacancies/<int:vacancy_id>/profile/edit/', views.profile_edit, name='profile_edit'),
    path('vacancies/<int:vacancy_id>/profile/generate-ai/', views.generate_profile_grades_ai, name='generate_profile_grades_ai'),
    path('profiles/<int:vacancy_id>/rerun-ai/', views.rerun_ai_profile_generation, name='rerun_ai_profile_generation'),
    path('profiles/', views.profiles_list, name='profiles_list'),
    path('profiles/update_field/', views.update_profile_grade_field, name='profile_grade_update_field'),
    path('vacancies/update_field/', views.update_vacancy_grade_field, name='vacancy_grade_update_field'),
    path('vacancy/update_field/', views.update_vacancy_field, name='vacancy_update_field'),
    path('profiles/<int:vacancy_id>/download_excel/', views.download_profile_grades_excel, name='download_profile_grades_excel'),
] 