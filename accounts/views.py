from django.shortcuts import redirect
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.shortcuts import render
from accounts.backend import is_ldap_user
from django.contrib.auth import login as djangoLogin
from django.contrib.auth.models import User
import os
from core import auth

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
    
    # if request.user.is_authenticated:
    #     return redirect('scheduler:landing_page')
    cwl = request.POST.get('cwl')
    password = request.POST.get('password')
    
    if cwl and password:
        
        result = auth.authenticate(cwl, password)
        
        if result:
            
            user = None
            
            if User.objects.filter(username=cwl).exists():
                user = User.objects.get(username=cwl)
            else:
                # Create a new user entry
                user = User.objects.create_user(
                    password=None, # Do not store password
                    username=cwl,
                    is_superuser=False,
                    is_staff=True,
                    is_active=True
                )
                user.save()
            
            djangoLogin(request, user)

            
            if user.is_staff and not user.is_superuser:
                return redirect('scheduler:landing_page_no_auth')
            elif user.is_staff and user.is_superuser:
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
    messages.success(request, 'See you again {}'.format(request.user))
    # clear_session(request)
    return redirect('accounts:ldap_logout')


def view_users(request):
    
    # if not request.user.is_authenticated:
    #     return redirect('accounts:ldap_login') # uncomment when auth works
    
    users_list = User.objects.all()
    
    return render(request, 'accounts/users/view_users.html', {
        'users': users_list
    })
    
def update_user(request, user_id):
    if request.method == 'POST':
        user = User.objects.get(id=user_id)
        print(user)
        data = request.POST
        
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        user.is_staff = data.get('is_staff', user.is_staff)
        user.is_active = data.get('is_active', user.is_active)
        user.is_staff = bool(data.get('is_staff')) 
        user.is_active = bool(data.get('is_active')) 

        user.save()

    return redirect('accounts:view_users')
# def create_user_page(request):
    
#     first_name
#     last_name
#     email
#     is_staff
#     is_active
    
    
#     user = User.objects.create(
#         first_name = first_name,
#         last_name = last_name,
#         email = email,
#         is_staff = is_staff,
#         is_active = is_active
#     )
    
#     return render(request, 'accounts/users/create_user.html')

def create_user(first_name, last_name, email, is_staff, is_active):
    
    first_name
    last_name
    email
    is_staff
    is_active
    
    
    user = User.objects.create(
        first_name = first_name,
        last_name = last_name,
        email = email,
        is_staff = is_staff,
        is_active = is_active
    )
    
    return user

