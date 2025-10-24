from django.urls import path
from scheduler import views

app_name = 'scheduler'

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('view_courses/', views.view_courses, name='view_courses'),
    path('update/<int:course_id>/', views.edit_course, name='edit_course'),
    path('create_course/', views.create_course, name='create_course'),
    
    # settings – course term
    path('setting_course_term/',    views.course_term_list,    name='course_term'),
    path("settings/course-term/create/", views.course_term_create, name="course_term_create"),
    path("settings/course-term/<int:pk>/update/", views.course_term_update, name="course_term_update"),
    path("settings/course-term/<int:pk>/delete/", views.course_term_delete, name="course_term_delete"),
    path("settings/course-term/<int:pk>/affected/", views.course_term_affected, name="course_term_affected"),

    # settings – course code
    path("setting_course_code/", views.course_code_list, name="course_code"),
    path("settings/course-code/create/", views.course_code_create, name="course_code_create"),
    path("settings/course-code/<int:pk>/update/", views.course_code_update, name="course_code_update"),
    path("settings/course-code/<int:pk>/delete/", views.course_code_delete, name="course_code_delete"),
    path("settings/course-code/<int:pk>/affected/", views.course_code_affected, name="course_code_affected"),

    # settings – course number
    path("setting_course_number/", views.course_number_list, name="course_number"),
    path("settings/course-number/create/", views.course_number_create, name="course_number_create"),
    path("settings/course-number/<int:pk>/update/", views.course_number_update, name="course_number_update"),
    path("settings/course-number/<int:pk>/delete/", views.course_number_delete, name="course_number_delete"),
    path("settings/course-number/<int:pk>/affected/", views.course_number_affected, name="course_number_affected"),

    # settings – course section
    path("setting_course_section/", views.course_section_list, name="course_section"),
    path("settings/course-section/create/", views.course_section_create, name="course_section_create"),
    path("settings/course-section/<int:pk>/update/", views.course_section_update, name="course_section_update"),
    path("settings/course-section/<int:pk>/delete/", views.course_section_delete, name="course_section_delete"),
    path("settings/course-section/<int:pk>/affected/", views.course_section_affected, name="course_section_affected"),

    # settings – course time
    path("setting_course_time/", views.course_time_list, name="course_time"),
    path("settings/course-time/create/", views.course_time_create, name="course_time_create"),
    path("settings/course-time/<int:pk>/update/", views.course_time_update, name="course_time_update"),
    path("settings/course-time/<int:pk>/delete/", views.course_time_delete, name="course_time_delete"),
    path("settings/course-time/<int:pk>/affected/", views.course_time_affected, name="course_time_affected"),

    # settings – course year
    path("setting_course_year/", views.course_year_list, name="course_year"),
    path("settings/course-year/create/", views.course_year_create, name="course_year_create"),
    path("settings/course-year/<int:pk>/update/", views.course_year_update, name="course_year_update"),
    path("settings/course-year/<int:pk>/delete/", views.course_year_delete, name="course_year_delete"),
    path("settings/course-year/<int:pk>/affected/", views.course_year_affected, name="course_year_affected"),

    # settings – program name
    path("setting_program_name/", views.program_name_list, name="program_name"),
    path("settings/program-name/create/", views.program_name_create, name="program_name_create"),
    path("settings/program-name/<int:pk>/update/", views.program_name_update, name="program_name_update"),
    path("settings/program-name/<int:pk>/delete/", views.program_name_delete, name="program_name_delete"),
    path("settings/program-name/<int:pk>/affected/", views.program_name_affected, name="program_name_affected"),

    # Requirements
    path('requirements/', views.requirements, name='requirements'),       
    # path('requirements/edit/', views.requirements_edit, name='requirements_edit'),
    path("requirements/levels/", views.ajax_levels_for_program, name="ajax_levels_for_program"),  

] 