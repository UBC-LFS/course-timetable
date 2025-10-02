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

    # settings – course code
    path("setting_course_code/", views.course_code_list, name="course_code"),
    path("settings/course-code/create/", views.course_code_create, name="course_code_create"),
    path("settings/course-code/<int:pk>/update/", views.course_code_update, name="course_code_update"),
    path("settings/course-code/<int:pk>/delete/", views.course_code_delete, name="course_code_delete"),

    # settings – course number
    path("setting_course_number/", views.course_number_list, name="course_number"),
    path("settings/course-number/create/", views.course_number_create, name="course_number_create"),
    path("settings/course-number/<int:pk>/update/", views.course_number_update, name="course_number_update"),
    path("settings/course-number/<int:pk>/delete/", views.course_number_delete, name="course_number_delete"),

    path('setting_course_section/', views.setting_course_section, name='course_section'),
    path('setting_course_time/',    views.setting_course_time,    name='course_time'),
    path('setting_course_year/',    views.setting_course_year,    name='course_year'),
    path('setting_program_name/', views.setting_program_name, name='program_name'),
] 