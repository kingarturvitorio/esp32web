from typing import Any
from django.shortcuts import render, redirect
from django.contrib.auth import logout
# Create your views here.
from django.contrib.auth.decorators import login_required
from django.views.generic.edit import CreateView, UpdateView
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User, Group
from .forms import SignUpForm, LoginForm
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404


from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from .forms import  SignUpForm, LoginForm, ForgotPasswordForm
from django.contrib.auth.models import User
import re
from django.core.mail import send_mail, BadHeaderError
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models.query_utils import Q
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')

from .models import Perfil

def user_login(request):
    if request.user.is_authenticated:
        return redirect('/')

    login_form = LoginForm(request.POST or None)
    if login_form.is_valid():
        username = login_form.cleaned_data.get('username')
        password = login_form.cleaned_data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('homedashboard')
        else:
            login_form.add_error('username', 'User with this profile was not found!')
    context = {
        'login_form': login_form,
        'title': "Login"
    }
    return render(request, 'usuarios/Login.html', context)


def user_signup(request):
    if request.user.is_authenticated:
        return redirect('/')
    signup_form = SignUpForm(request.POST or None)

    if signup_form.is_valid():
        username = signup_form.cleaned_data.get('username')
        email = signup_form.cleaned_data.get('email')
        password = signup_form.cleaned_data.get('password')

        User.objects.create_user(
            username=username, email=email, password=password)
        return redirect('/login')
    context = {
        'signup_form': signup_form,
        'title': "Register"
    }
    return render(request, 'usuarios/SignUp.html', context)


def password_reset_request(request):
    if request.user.is_authenticated:
        return redirect('/')
    passform = ForgotPasswordForm(request.POST )
    add_error = False
    if request.method == "POST" :
        # A form bound to the POST data
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():  # All validation rules pass
            myfield = form.cleaned_data['Username']
            is_exists_user = User.objects.filter(email=myfield).exists()
            associated_users = User.objects.filter(Q(email=myfield))
            if len(request.POST['Username']) < 1 or not EMAIL_REGEX.match(request.POST['Username']) or not is_exists_user:
                add_error = True
            if associated_users.exists():
                for user in associated_users:
                    subject = "Password Reset Requested"
                    email_template_name = "password_reset_email.txt"
                    c = {
                        "email": user.email,
                        'domain': '127.0.0.1:8000',
                        'site_name': 'Website',
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "user": user,
                        'token': default_token_generator.make_token(user),
                        'protocol': 'http',
					}
                    email = render_to_string(email_template_name, c)
                    try:
                        send_mail(subject, email, 'admin@example.com',[user.email], fail_silently=False)
                    except BadHeaderError:
                        return HttpResponse('Invalid header found.')
                    return render(request, 'password_reset_done.html', {'title': "Successful"})

    
    context = {
        'forgot_password_form': passform,
        
        'valid_error': add_error,
        'title': "Forgot Password"
    }
    return render(request, 'usuarios/password_reset.html', context)

class PerfilUpdate(UpdateView):
    template_name = "cadastros/form.html"
    model = Perfil
    fields = ["nome_completo", "cpf", "telefone"]
    success_url = reverse_lazy("index")

    def get_object(self, queryset=None):
        self.object = get_object_or_404(Perfil, usuario=self.request.user)
        return self.object
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args ,**kwargs)
        
        context["titulo"] = "Meus dados pessoais"
        context["botao"] = "Atualizar"

        return 
    

@login_required
def logout_view(request):
    logout(request)
    return render(request, 'usuarios/login.html')