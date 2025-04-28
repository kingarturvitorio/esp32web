from django.urls import path
from . import views


urlpatterns = [
    path('listar_dispositivos/', views.DispositivoListView.as_view(), name='lista-dispositivos'),
    path('sistema_monitoramento/', views.SistemaMonitoramentoView.as_view(), name='sistema-monitoramento'),
    path('criar_dispositivo/', views.DispositivoCreateView.as_view(), name='criar-dispositivos'),
    path('<int:pk>/editar/', views.DispositivoUpdateView.as_view(), name='editar-dispositivos'),
    path('<int:pk>/detalhe/', views.DispositivoDetailView.as_view(), name='detalhar-dispositivos'),
    path('<int:pk>/deletar/', views.DispositivoDeleteView.as_view(), name='deletar-dispositivos'),

    ##rota para ser atualizada dinamicamente via ajax
    path("api/status-dispositivos/", views.status_dispositivos, name="status-dispositivos"),
]