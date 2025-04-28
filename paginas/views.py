from django.shortcuts import render

from django.views.generic import TemplateView

# Create your views here.

class IndexView(TemplateView):
    template_name = 'site/modelo_site.html'

class SobreView(TemplateView):
    template_name = 'paginas/sobre.html'

class AtuadoresSensoresView(TemplateView):
    template_name = 'paginas/atuadoressensores.html'

class GraficosView(TemplateView):
    template_name = 'paginas/graficos.html'

class TccView(TemplateView):
    template_name = 'paginas/tcc.html'

class PesquisaView(TemplateView):
    template_name = 'paginas/pesquisa.html'

class EstagioView(TemplateView):
    template_name = 'paginas/estagio.html'

class AlunosView(TemplateView):
    template_name = 'paginas/alunos.html'

class ProjetosView(TemplateView):
    template_name = 'paginas/projetos.html'

class AulasView(TemplateView):
    template_name = 'paginas/aulas.html'

class ContatosView(TemplateView):
    template_name = 'paginas/contato.html'


