from django.urls import path
from django.contrib.auth import views as auth_views

from .views import *

urlpatterns = [
    #path('', view, name=""),
    path('', user_login, name='index'),
    path('logout/', logout_view, name='logout'),
    path('registra/', user_signup, name='registrar'),
    path('atualizar-dados/', PerfilUpdate.as_view(), name='atualizar-dados'),
    
    path("password_reset", password_reset_request, name="password_reset"),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='templates/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name="password_confirm.html"), name='password_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),  
]