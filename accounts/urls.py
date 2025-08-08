from django.urls import path, include
from accounts import views

app_name = 'accounts'


urlpatterns = [
    path('login/', views.ldap_login, name='ldap_login'),
    path('logout/', views.ldap_logout, name='ldap_logout'),
    path('view/', views.view_users, name='view_users'),
    path('create_user/', views.create_user, name='create_user'),
    path('update/<int:user_id>/', views.update_user, name='update_user'),
    path('delete/<int:user_id>/', views.delete_user, name='delete_user')
]
