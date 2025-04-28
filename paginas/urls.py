from django.urls import path
from .views import IndexView, SobreView, AtuadoresSensoresView, GraficosView, TccView, PesquisaView, EstagioView, AulasView, ProjetosView, AlunosView, ContatosView

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('sobre/', SobreView.as_view(), name='sobre'),
    path('atuadoressensores/', AtuadoresSensoresView.as_view(), name='atuadoressensores'),
    path('graficos/', GraficosView.as_view(), name='graficos'),
    path('tcc/', TccView.as_view(), name='tcc'),
    path('pesquisa/', PesquisaView.as_view(), name='pesquisa'),
    path('estagio/', EstagioView.as_view(), name='estagio'),
    path('aulas/', AulasView.as_view(), name='aulas'),
    path('projetos/', ProjetosView.as_view(), name='projetos'),
    path('alunos/', AlunosView.as_view(), name='alunos'),
    path('contato/', ContatosView.as_view(), name='contato'),

]