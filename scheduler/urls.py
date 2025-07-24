from django.urls import path
from scheduler import views

app_name = 'scheduler'

urlpatterns = [
    path('home/', views.landing_page, name='landing_page'),
] 