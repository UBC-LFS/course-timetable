from django.urls import path, include
from accounts import views

app_name = 'accounts'


urlpatterns = [
    path('login/', views.ldap_login, name='ldap_login'),
    path('logout/', views.ldap_logout, name='ldap_logout'),
    path('view/', views.view_users, name='view_users'),
    path('create_user/', views.create_user, name='create_user'),
    path('update/<int:user_id>/', views.update_user, name='update_user'),
    path('delete/<int:user_id>/', views.delete_user, name='delete_user'),
    
    path('admin_role/', views.role_list, name='role'),
    path("admin/role/create/", views.role_create, name="role_create"),
    path("admin/role/<int:pk>/update/", views.role_update, name="role_update"),
    path("admin/role/<int:pk>/delete/", views.role_delete, name="role_delete"),
    path("admin/role/<int:pk>/affected/", views.role_affected, name="role_affected"),
]
