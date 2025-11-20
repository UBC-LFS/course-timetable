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

# Create your views here.

'''
General flow:
1. User logs in from login page.html
2. Info from form is passed into this view
    info:
        username, password
3. Check if form is valid
4. Check accounts with django auth
5. Use the backend.py is_ldap_user method for utilizing LDAP
6. if user auth then go to home page
   else send error

'''

#TODO: Below
'''
1. create auth.authenticate function in another file
- Use accounts -> views.py login functionality from inventory
    - look at custom authenticate function (not djangos)
        - don't need to make custom model just check is is_superuser and is _staff false or true

2. where Profile.objects.filter(cwl=cwl) is put a check for roles
    - Checking superuser and staff here

3.
- Use built in django login after all checks
'''


@never_cache
def ldap_login(request):
    '''
    1. If result is valid then by default the person is a staff member
    2. Now we need to check if they are a superuser
        - This can only be assigned through another superuser
    3. 
    '''
    
    '''Everyone that passes here will be inside of LFS, but you need to check if they have authority within LFS by checking their user attributes'''
    
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
                Profile.objects.get_or_create(user= user, role= user_role)
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
def role_list(request):
    roles = Role.objects.all()
    form = RoleForm()
    return render(request, "accounts/role_list.html", {"roles": roles, "form": form})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
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
@require_POST
def role_delete(request, pk):
    role = get_object_or_404(Role, pk=pk)
    role.delete()
    messages.success(request, "Role deleted.")
    return redirect("accounts:role")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def view_users(request):
    users_list = User.objects.all()
    
    return render(request, 'accounts/users/view_users.html', {
        'users': users_list
    })

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login') 
def update_user(request, user_id):
    if request.method == 'POST':
        user = User.objects.get(id=user_id)
        print(user)
        data = request.POST
        
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.username = data.get('cwl', user.username)
        user.email = data.get('email', user.email)
        user.is_staff = data.get('is_staff', user.is_staff)
        user.is_active = data.get('is_active', user.is_active)
        user.is_staff = bool(data.get('is_staff')) 
        user.is_active = bool(data.get('is_active')) 

        user.save()

    return redirect('accounts:view_users')

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def create_user(request):
    
    first_name = request.POST.get('first_name', '')
    last_name = request.POST.get('last_name', '')
    email = request.POST.get('email', '')
    is_staff = request.POST.get('is_staff', False)
    is_active = request.POST.get('is_active', False)
    
    if not first_name or not last_name or not email:
       print('First name, last name, and email are required.')
       return render(request, 'accounts/users/create_user.html')

    if User.objects.filter(email=email).exists():
        print('A user with this email already exists.')
        return render(request, 'accounts/users/create_user.html')

    if is_staff == 'on':
        is_staff = True
    else:
        is_staff = False

    if is_active == 'on':
        is_active = True
    else:
        is_active = False

    print(first_name, last_name, email, is_staff, is_active)
    
    
    User.objects.create(
        username=request.POST.get("cwl"),
        first_name=first_name,
        last_name=last_name,
        email=email,
        is_staff=is_staff,
        is_active=is_active
    )

    return redirect('accounts:view_users')

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def delete_user(request, user_id):
    user = User.objects.get(id=user_id)
    try:
        user.delete()
        print("User Successfully deleted")
    except Exception as e:
        print(f"Error deleting user {user_id}: {e}")
    return redirect('accounts:view_users')

