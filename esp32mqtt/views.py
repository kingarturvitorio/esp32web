from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from . models import Dispositivo
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

class DispositivoCreateView(LoginRequiredMixin, CreateView):
    model = Dispositivo
    fields = ['nome', 'identificador', 'descricao']
    template_name = 'criar_dispositivos.html'
    success_url = reverse_lazy('lista-dispositivos')

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)

class DispositivoListView(LoginRequiredMixin, ListView):
    model = Dispositivo
    template_name = 'listar_dispositivos.html'

    def get_queryset(self):
        return Dispositivo.objects.filter(usuario=self.request.user)
    
class DispositivoUpdateView(LoginRequiredMixin, UpdateView):
    model = Dispositivo
    fields = ['nome', 'identificador', 'descricao']
    template_name = 'editar_dispositivos.html'
    success_url = reverse_lazy('lista-dispositivos')

class DispositivoDeleteView(LoginRequiredMixin, DeleteView):
    model = Dispositivo
    template_name = 'excluir_dispositivos.html'
    success_url = reverse_lazy('lista-dispositivos')

class DispositivoDetailView(DetailView):
    model = Dispositivo
    template_name = 'detalhe_dispositivos.html'

##view para retornar via ajax de forma automatica na tela
def status_dispositivos(request):
    dispositivos = Dispositivo.objects.all()
    data = {}

    for d in dispositivos:
        online = (timezone.now() - d.ultimo_ping) < timedelta(seconds=60) if d.ultimo_ping else False
        print(d)
        data[d.identificador] = "online" if online else "offline"

    return JsonResponse(data)

class SistemaMonitoramentoView(LoginRequiredMixin, ListView):
    model = Dispositivo
    template_name = 'sistema_monitoramento.html'