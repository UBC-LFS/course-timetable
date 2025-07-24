from django.urls import path, include
from authentication import views

app_name = 'authentication'


urlpatterns = [
    path('login/', views.ldap_login, name='ldap_login'),
    path('logout/', views.ldap_logout, name='ldap_logout')
] 
