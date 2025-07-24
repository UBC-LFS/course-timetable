from django.shortcuts import redirect
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.shortcuts import render
from authentication.backend import is_ldap_user

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

#TODO: Get CWL and Password from template and pass it into ldap

@never_cache
def ldap_login(request):
    
    if request.method == 'POST':
        if request.POST.get('cwl') and request.POST.get('password'):
            if is_ldap_user(request.POST.get('cwl'), request.POST.get('password')):
                messages.success(request, 'Welcome back {}'.format(request.user))
                return redirect('scheduler:landing_page')
            else:
                messages.error(request, 'Invalid CWL or password, please try again')
                return redirect('authentication:ldap_login')
        else:
            messages.error(request, 'Please enter both CWL and Password')
            return redirect('authentication:ldap_login')
    
    return render(request, 'authentication/login.html') 

@never_cache
def ldap_logout(request):
    messages.success(request, 'See you again {}'.format(request.user))
    # logout(request)
    # clear_session(request)
    return redirect('index')
