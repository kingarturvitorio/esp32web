import json
import redis
from django.conf       import settings
from django.shortcuts  import render, redirect
from django.http       import JsonResponse
from django.urls       import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from .models           import Cartao, EventoAcesso
from esp32mqtt.models  import Dispositivo
from .commands         import enviar_comando_open_lock
from django.views.generic import (
    ListView, CreateView, UpdateView, DetailView, DeleteView
)
from django.urls import reverse_lazy

User = get_user_model()

def dashboard(request):
    dispositivos = Dispositivo.objects.all()
    eventos       = EventoAcesso.objects.order_by('-timestamp')[:50]
    return render(request, "controle_acesso/dashboard.html", {
        "dispositivos": dispositivos,
        "eventos": eventos,
    })

def enroll_page(request):
    return render(request, "controle_acesso/enroll.html")

@csrf_exempt
def enroll_card(request):
    """
    POST JSON { uid, username } → cria/associa Cartao↔User
    """
    if request.method != "POST":
        return JsonResponse({"error": "Método não permitido"}, status=405)
    data = json.loads(request.body)
    uid      = data.get("uid")
    username = data.get("username")
    if not uid or not username:
        return JsonResponse({"error": "uid e username obrigatórios"}, status=400)

    user, _    = User.objects.get_or_create(username=username)
    cartao, c  = Cartao.objects.get_or_create(
        uid=uid,
        defaults={"usuario": user}
    )
    if not c and cartao.usuario != user:
        cartao.usuario = user
        cartao.save()

    return JsonResponse({
        "uid": uid,
        "usuario": user.username,
        "created": c
    })

def abrir_tranca(request, identificador):
    """
    Chama o comando de abertura via Redis → mqtt_consumer → ESP32
    """
    enviar_comando_open_lock(identificador)
    return redirect(reverse("controle_acesso:dashboard"))


class CartaoListView(ListView):
    model = Cartao
    template_name = 'controle_acesso/cartao_list.html'
    context_object_name = 'cartoes'

class CartaoCreateView(CreateView):
    model = Cartao
    fields = ['uid', 'usuario', 'ativo']
    template_name = 'controle_acesso/cartao_form.html'
    success_url = reverse_lazy('controle_acesso:cartao_list')

    def get_initial(self):
        initial = super().get_initial()
        # pré-preenche o campo uid se vier como parâmetro GET
        uid = self.request.GET.get('uid')
        if uid:
            initial['uid'] = uid
        return initial

class CartaoUpdateView(UpdateView):
    model = Cartao
    fields = ['uid', 'usuario', 'ativo']
    template_name = 'controle_acesso/cartao_form.html'
    success_url = reverse_lazy('controle_acesso:cartao_list')

class CartaoDeleteView(DeleteView):
    model = Cartao
    template_name = 'controle_acesso/cartao_confirm_delete.html'
    success_url = reverse_lazy('controle_acesso:cartao_list')




#####################evento de acesso###

class EventoAcessoListView(ListView):
    model = EventoAcesso
    template_name = 'controle_acesso/evento_list.html'
    context_object_name = 'eventos'
    def get_queryset(self):
        """
        Retorna somente os 100 eventos mais recentes, ordenados por timestamp descendente.
        """
        return EventoAcesso.objects.order_by('-timestamp')[:100]

class EventoAcessoDetailView(DetailView):
    model = EventoAcesso
    template_name = 'controle_acesso/evento_detail.html'
    context_object_name = 'evento'

class EventoAcessoCreateView(CreateView):
    model = EventoAcesso
    fields = ['cartao', 'dispositivo', 'autorizado']
    template_name = 'controle_acesso/evento_form.html'
    success_url = reverse_lazy('controle_acesso:evento_list')

class EventoAcessoUpdateView(UpdateView):
    model = EventoAcesso
    fields = ['cartao', 'dispositivo', 'autorizado']
    template_name = 'controle_acesso/evento_form.html'
    success_url = reverse_lazy('controle_acesso:evento_list')

class EventoAcessoDeleteView(DeleteView):
    model = EventoAcesso
    template_name = 'controle_acesso/evento_confirm_delete.html'
    success_url = reverse_lazy('controle_acesso:evento_list')

class EventoAcessoFilterView(ListView):
    model = EventoAcesso
    template_name = 'controle_acesso/evento_filter.html'
    context_object_name = 'eventos'

    def get_queryset(self):
        qs = EventoAcesso.objects.select_related('cartao', 'cartao__usuario')
        # filtros via GET
        uid = self.request.GET.get('uid')
        usuario = self.request.GET.get('usuario')
        dispositivo = self.request.GET.get('dispositivo')

        if uid:
            qs = qs.filter(cartao__uid__icontains=uid)
        if usuario:
            qs = qs.filter(cartao__usuario__username__icontains=usuario)
        if dispositivo:
            qs = qs.filter(dispositivo__icontains=dispositivo)

        return qs.order_by('-timestamp')[:100]