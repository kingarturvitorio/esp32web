from django.urls import path
from . import views

app_name = "controle_acesso"

urlpatterns = [
    path("", views.dashboard,      name="dashboard"),
    path("enroll/", views.enroll_page,  name="enroll_page"),
    path("api/enroll_card/", views.enroll_card, name="enroll_card"),
    path("abrir_tranca/<str:identificador>/", views.abrir_tranca, name="abrir_tranca"),
]
