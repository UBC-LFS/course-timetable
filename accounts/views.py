from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.shortcuts import render
from django.contrib.auth import login as djangoLogin, logout as djangoLogout
from django.contrib.auth.models import User
from core import auth
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from scheduler.models import (Profile, Role)
from scheduler.forms import RoleForm
from django.views.decorators.http import require_POST
from functools import wraps

# Create your views here.

'''
General flow:
1. User logs in from login.html
2. Info from form is passed into this view
    info:
        username, password
3. Use the backend.py is_ldap_user() for utilizing LDAP
4. Use built in django login after all checks
5. if user auth then go to home page
   else send error
'''

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # If this decorator is stacked under @login_required,
        # request.user is guaranteed to be authenticated here.
        user = request.user

        profile = Profile.objects.select_related("role").get(user=user)
        role_name = (profile.role.name if profile.role else "")
        if role_name != "Admin":
            messages.error(request, "You do not have permission to access this page.")
            return redirect("scheduler:landing_page")

        return view_func(request, *args, **kwargs)

    return _wrapped_view

@never_cache
def ldap_login(request):
    
    cwl = request.POST.get('cwl')
    password = request.POST.get('password')
    
    if cwl and password:
        
        result = auth.authenticate(cwl, password)
        if result:
            
            user = None

            if User.objects.filter(username=cwl).exists():
                user = User.objects.get(username=cwl)
            else:
                user = User.objects.create_user(
                    password=None,
                    username=cwl,
                )
                user.save()
            
            user_role, _ = Role.objects.get_or_create(name= "User")
            Profile.objects.get_or_create(user=user, defaults={"role": user_role})

            if user:
                djangoLogin(request, user)
                return redirect('scheduler:landing_page')
                
            else:
                messages.error(request, 'An error occurred. No Access.')
                return redirect('accounts:ldap_login')
                        
        else:
            messages.error(request, 'An error occurred. You have entered incorrect CWL or Password. Or, your CWL ID does not exist. Please contact your system administrator.')
    
    return render(request, 'accounts/login.html', {
        
    })

@never_cache
def ldap_logout(request):
    djangoLogout(request)
    return redirect('accounts:ldap_login')

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@admin_required
def role_affected(request, pk):
    """
    Return all profiles currently pointing at this Role.
    Used by the preview modal for both edit and delete.
    """
    role = get_object_or_404(Role, pk=pk)
    qs = (Profile.objects
          .filter(role=role)
          .select_related("user", "role")
          .order_by("role__name"))

    items = [{
        "role": getattr(p.role, "name", "") or "None",
        "username": getattr(p.user, "username", "") or "None",
        "first_name": getattr(p.user, "first_name", "") or "None",
        "last_name": getattr(p.user, "last_name", "") or "None",
    } for p in qs]

    return JsonResponse({"count": len(items), "items": items})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@admin_required
def role_list(request):
    roles = Role.objects.all()
    form = RoleForm()
    return render(request, "accounts/role_list.html", {"roles": roles, "form": form})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@admin_required
@require_POST
def role_create(request):
    form = RoleForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Role created.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("accounts:role")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@admin_required
@require_POST
def role_update(request, pk):
    role = get_object_or_404(Role, pk=pk)
    form = RoleForm(request.POST, instance=role)
    if form.is_valid():
        form.save()
        messages.success(request, "Role edited.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Edit failed: {err}")
    return redirect("accounts:role")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@admin_required
@require_POST
def role_delete(request, pk):
    role = get_object_or_404(Role, pk=pk)
    role.delete()
    messages.success(request, "Role deleted.")
    return redirect("accounts:role")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@admin_required
def view_profiles(request):
    # By convention, we display User table instead of Profile table.
    # Since User and Profile are one to one relationship, displaying User table is the same as displaying Profile table.
    users = User.objects.all().order_by("username")
    roles = Role.objects.all().order_by("name")

    return render(request, 'accounts/profile_list.html', {
        'users': users,
        'roles': roles,
    })

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@admin_required 
@require_POST
def update_profile(request, pk):
    profile = get_object_or_404(
        Profile.objects.select_related("user", "role"),
        pk=pk,
    )
    user = profile.user

    first_name = (request.POST.get("first_name") or "").strip()
    last_name = (request.POST.get("last_name") or "").strip()
    cwl = (request.POST.get("cwl") or "").strip()
    role_id = request.POST.get("role")

    # Duplicate CWL check
    if User.objects.filter(username__exact=cwl).exclude(pk=user.pk).exists():
        messages.error(request, "Edit failed: A user with this CWL already exists.")
        return redirect("accounts:view_profiles")

    role = get_object_or_404(Role, pk=role_id)

    # Update User
    user.username = cwl
    user.first_name = first_name
    user.last_name = last_name
    user.save()

    # Update Profile
    profile.role = role
    profile.save(update_fields=["role"])

    messages.success(request, "User edited.")
    return redirect("accounts:view_profiles")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@admin_required
@require_POST
def create_profile(request):
    """
    Create a new User + Profile.

    - First Name -> user.first_name
    - Last Name  -> user.last_name
    - CWL        -> user.username
    - Role       -> Profile.role
    """
    first_name = (request.POST.get("first_name") or "").strip()
    last_name = (request.POST.get("last_name") or "").strip()
    cwl = (request.POST.get("cwl") or "").strip()
    role_id = request.POST.get("role")

    # Duplicate CWL check 
    if User.objects.filter(username__exact=cwl).exists():
        messages.error(request, "Create failed: A user with this CWL already exists.")
        return redirect("accounts:view_profiles")

    # Resolve Role
    role = get_object_or_404(Role, pk=role_id)

    # Create User
    user = User.objects.create_user(
        username=cwl,
        password=None,
        first_name=first_name,
        last_name=last_name,
    )
    user.save()

    # Create Profile
    Profile.objects.create(user=user, role=role)

    messages.success(request, "User created.")
    return redirect("accounts:view_profiles")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@admin_required
@require_POST
def delete_profile(request, pk):
    profile = get_object_or_404(Profile.objects.select_related("user"), pk=pk)
    user = profile.user

    # Deleting the User will also delete Profile (on_delete=CASCADE)
    user.delete()

    messages.success(request, "User deleted.")
    return redirect("accounts:view_profiles")
