from django.shortcuts import redirect
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.shortcuts import render
from accounts.backend import is_ldap_user
from django.contrib.auth import login as djangoLogin

# Create your views here.

'''
General flow:
1. User logs in from login page.html
2. Info from form is passed into this view
    info:
        username, password
3. Check if form is valid
4. Check authentication with django auth
5. Use the backend.py is_ldap_user method for utilizing LDAP
6. if user auth then go to home page
   else send error

'''

#TODO: Below
'''
1. create auth.authenticate function in another file
- Use accounts -> views.py login functionality from inventory
    - look at custom authenticate function (not djangos)
        - don't need to make model!

2. where Profile.objects.filter(cwl=cwl) is put a check for roles
    - Checking superuser and staff here

3.
- Use built in django login after all checks
'''

@never_cache
def ldap_login(request):
    # result = auth.authenticate(cwl, password)
    # if result:
    #     # profile_obj = Profile.objects.filter(cwl=cwl)
        
    #     if True :
    #     # if profile_obj.exists():
    #         user = profile_obj.first().user
    #         if not user.email or not user.is_staff or not user.is_active:
    #             return redirect('accounts:login_error')

    #         djangoLogin(request, user)
    #         return redirect('inventory:home')
    #     else:
    #         return redirect('accounts:login_error')
    # else:
    #     messages.error(request, 'An error occurred. You have entered incorrect CWL or Password. Or, your CWL ID does not exist. Please contact your system administrator.')
    
    
    
    
    cwl = request.POST.get('cwl')
    password = request.POST.get('password')
    
    if request.method == 'POST':
        if cwl and password and is_ldap_user(cwl, password):
            messages.success(request, 'Welcome back {}'.format(request.user))
            return redirect('scheduler:landing_page')
        else:
            messages.error(request, 'Invalid CWL or password, please try again')
            return redirect('authentication:ldap_login')

    return render(request, 'authentication/login.html') 

@never_cache
def ldap_logout(request):
    messages.success(request, 'See you again {}'.format(request.user))
    # clear_session(request)
    return redirect('authentication:ldap_logout')

