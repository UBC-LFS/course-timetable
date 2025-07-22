from django.views import View
from django.shortcuts import redirect
from django.contrib.auth import authenticate, logout, clear_session
from django.views.generic.edit import FormView
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator

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

# if is_ldap_user(cwl, password):
#             messages.success(self.request, 'Welcome back {}'.format(self.request.user))
#             return redirect('inventory:home')
#         else:
#             messages.error(self.request, 'Invalid CWL or password, please try again')
#             return redirect('authentication:login')


'''--------------------- OLD CODE -----------------------------------'''
# @method_decorator([never_cache], name='dispatch')
# class LoginView(FormView):
#     template_name = 'authentication/login.html'

#     def form_valid(self, form):
#         email = form.cleaned_data.get('email')
#         cwl = form.cleaned_data.get('cwl')
#         password = form.cleaned_data.get('password')
        
#         user = authenticate(self.request, email=email) 
#         if not user:
#             messages.error(self.request, 'Invalid email address, please try again')
#             return redirect('authentication:login')

#         if is_ldap_user(cwl, password):
#             messages.success(self.request, 'Welcome back {}'.format(self.request.user))
#             return redirect('inventory:home')
#         else:
#             messages.error(self.request, 'Invalid CWL or password, please try again')
#             return redirect('authentication:login')


# @method_decorator([never_cache], name='dispatch')
# class LogoutView(View):
#     def get(self, request):
#         messages.success(request, 'See you again {}'.format(request.user))
#         logout(self.request)
#         clear_session(self.request)
#         return redirect('index')