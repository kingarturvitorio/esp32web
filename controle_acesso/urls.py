from django.urls import path
from . import views

from .views import (
    CartaoListView,
    CartaoCreateView,
    CartaoUpdateView,
    CartaoDeleteView,
)

from .views import (
    EventoAcessoListView,
    EventoAcessoDetailView,
    EventoAcessoCreateView,
    EventoAcessoUpdateView,
    EventoAcessoDeleteView,
    EventoAcessoFilterView,
)


app_name = "controle_acesso"

urlpatterns = [
    path("", views.dashboard,      name="dashboard"),
    path("enroll/", views.enroll_page,  name="enroll_page"),
    path("api/enroll_card/", views.enroll_card, name="enroll_card"),
    path("abrir_tranca/<str:identificador>/", views.abrir_tranca, name="abrir_tranca"),

    path('cartoes/', CartaoListView.as_view(),   name='cartao_list'),
    path('cartoes/add/', CartaoCreateView.as_view(), name='cartao_add'),
    path('cartoes/<int:pk>/edit/',  CartaoUpdateView.as_view(), name='cartao_edit'),
    path('cartoes/<int:pk>/delete/', CartaoDeleteView.as_view(), name='cartao_delete'),


    # CRUD de EventoAcesso
    path('eventos/', EventoAcessoListView.as_view(), name='evento_list'),
    path('eventos/add/', EventoAcessoCreateView.as_view(), name='evento_add'),
    path('eventos/<int:pk>/', EventoAcessoDetailView.as_view(), name='evento_detail'),
    path('eventos/<int:pk>/edit/', EventoAcessoUpdateView.as_view(), name='evento_edit'),
    path('eventos/<int:pk>/delete/', EventoAcessoDeleteView.as_view(), name='evento_delete'),
    path('eventos/filtrar/', EventoAcessoFilterView.as_view(), name='evento_filter'),
]
