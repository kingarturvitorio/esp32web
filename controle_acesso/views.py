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
