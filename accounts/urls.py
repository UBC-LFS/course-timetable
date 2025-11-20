from django.urls import path, include
from accounts import views

app_name = 'accounts'


urlpatterns = [
    path('login/', views.ldap_login, name='ldap_login'),
    path('logout/', views.ldap_logout, name='ldap_logout'),

    path('view/', views.view_profiles, name='view_profiles'),
    path('create/', views.create_profile, name='create_profile'),
    path('update/<int:pk>/', views.update_profile, name='update_profile'),
    path('delete/<int:pk>/', views.delete_profile, name='delete_profile'),
    
    path('admin_role/', views.role_list, name='role'),
    path("admin/role/create/", views.role_create, name="role_create"),
    path("admin/role/<int:pk>/update/", views.role_update, name="role_update"),
    path("admin/role/<int:pk>/delete/", views.role_delete, name="role_delete"),
    path("admin/role/<int:pk>/affected/", views.role_affected, name="role_affected"),
]
