from django.views import View
from django.shortcuts import redirect
from django.contrib.auth import authenticate
from django.views.generic.edit import FormView
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator

from include.session.session import unset_checkout_access_only_session

from .forms import LoginForm

from authentication.backend import is_ldap_user

from include.login.login import loginWithCheckoutAccessOnly, logoutAndClearSession

# Create your views here.

@method_decorator([never_cache], name='dispatch')
class LoginView(FormView):
    template_name = 'authentication/login.html'
    form_class = LoginForm

    def form_valid(self, form):
        email = form.cleaned_data.get('email')
        cwl = form.cleaned_data.get('cwl')
        password = form.cleaned_data.get('password')

        user = authenticate(self.request, email=email)
        if not user:
            messages.error(self.request, 'Invalid email address, please try again')
            return redirect('authentication:login')
        else:
            loginWithCheckoutAccessOnly(self.request, user)

        if is_ldap_user(cwl, password):
            unset_checkout_access_only_session(self.request)
            messages.success(self.request, 'Welcome back {}'.format(self.request.user))
            return redirect('inventory:home')
        else:
            messages.error(self.request, 'Invalid CWL or password, please try again')
            return redirect('authentication:login')


@method_decorator([never_cache], name='dispatch')
class LogoutView(View):
    def get(self, request):
        messages.success(request, 'See you again {}'.format(request.user))
        logoutAndClearSession(self.request)
        return redirect('index')