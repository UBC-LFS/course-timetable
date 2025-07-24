from django.urls import path, include
from accounts import views

app_name = 'accounts'


urlpatterns = [
    path('login/', views.ldap_login, name='ldap_login'),
    path('logout/', views.ldap_logout, name='ldap_logout')
] 
