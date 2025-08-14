from django.urls import path
from scheduler import views

app_name = 'scheduler'

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('view_courses/', views.view_courses, name='view_courses'),
    path('update/<int:course_id>/', views.edit_course, name='edit_course'),
    path('create_course/', views.create_course, name='create_course')

] 