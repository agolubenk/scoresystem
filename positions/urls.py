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
    
    # URLs для вопросов интервью
    path('questions/', views.questions_list, name='questions'),
    path('questions/create/', views.create_question, name='create_question'),
    path('questions/<int:question_id>/update/', views.update_question, name='update_question'),
    path('questions/<int:question_id>/delete/', views.delete_question, name='delete_question'),
    
    # Матрицы пересчета баллов
    path('score-matrices/', views.score_matrices, name='score_matrices'),
    path('score-matrices/create/', views.create_score_matrix, name='create_score_matrix'),
    path('score-matrices/<int:matrix_id>/edit/', views.edit_score_matrix, name='edit_score_matrix'),
    path('score-matrices/<int:matrix_id>/delete/', views.delete_score_matrix, name='delete_score_matrix'),
    path('score-matrices/<int:matrix_id>/toggle/', views.toggle_matrix_active, name='toggle_matrix_active'),
    path('score-matrices/<int:matrix_id>/download/', views.download_score_matrix, name='download_score_matrix'),
    path('score-matrices/<int:matrix_id>/upload/', views.upload_score_matrix, name='upload_score_matrix'),
    path('interview/create/', views.InterviewCreateView.as_view(), name='interview_create'),
    path('interview/<int:pk>/conduct/', views.InterviewConductView.as_view(), name='interview_conduct'),
    path('interview/<int:pk>/result/', views.InterviewResultView.as_view(), name='interview_result'),
    path('interview/<int:pk>/download/', views.download_interview_results, name='interview_download'),
    path('interview/<int:pk>/delete/', views.delete_interview, name='interview_delete'),
    path('interview/<int:pk>/rerun-ai/', views.rerun_ai_analysis, name='rerun_ai_analysis'),
    path('interviews/', views.InterviewListView.as_view(), name='interview_list'),
    path('candidates/', views.CandidateListView.as_view(), name='candidate_list'),
    path('candidates/create/', views.CandidateCreateView.as_view(), name='candidate_create'),
    path('candidates/<int:pk>/', views.CandidateDetailView.as_view(), name='candidate_detail'),
    path('candidates/<int:pk>/edit/', views.CandidateUpdateView.as_view(), name='candidate_edit'),
    path('candidates/<int:pk>/delete/', views.CandidateDeleteView.as_view(), name='candidate_delete'),
    path('candidates/<int:pk>/resume-preview/', views.CandidateResumePreviewView.as_view(), name='candidate_resume_preview'),
    path('candidates/<int:pk>/resume-view/', views.candidate_resume_view, name='candidate_resume_view'),
    path('test-template/<int:question_id>/update/', views.update_test_template, name='update_test_template'),
    path('candidate/<int:pk>/', views.candidate_detail, name='candidate_detail'),
    path('candidate/<int:pk>/update/', views.candidate_update, name='candidate_update'),
    path('candidate/<int:pk>/files/upload/', views.candidate_files_upload, name='candidate_files_upload'),
    path('candidate/file/<int:file_id>/delete/', views.candidate_file_delete, name='candidate_file_delete'),
    path('candidate/<int:pk>/tasks/', views.candidate_tasks, name='candidate_tasks'),
    path('candidate/<int:pk>/add_comment/', add_candidate_comment, name='add_candidate_comment'),
    path('candidate/comment/<int:comment_id>/edit/', edit_candidate_comment, name='edit_candidate_comment'),
    path('grades/reorder/', views.reorder_grades, name='reorder_grades'),
] 