import json
from django.utils import timezone
from esp32mqtt.models import Dispositivo, Medicao
from .base import channel_layer
from asgiref.sync import async_to_sync

def handle_mqtt_message(topic: str, payload: bytes):
    """Processa cada mensagem MQTT recebida."""
    parts = topic.split('/')
    identificador, tipo_dado = parts[1], parts[2]
    valor = payload.decode()

    # atualiza último ping
    disp = Dispositivo.objects.get(identificador=identificador)
    disp.ultimo_ping = timezone.now()
    disp.save()

    # persiste leitura numérica
    try:
        Medicao.objects.create(
            dispositivo=disp,
            tipo=tipo_dado,
            valor=float(valor)
        )
    except ValueError:
        pass

    # notifica via WebSocket
    async_to_sync(channel_layer.group_send)(
        "esp32_status",
        {
            "type": "send_status",
            "data": {
                "identificador": identificador,
                "tipo": tipo_dado,
                "valor": valor,
                "status": "online",
                "timestamp": timezone.now().isoformat()
            }
        }
    )

def handle_redis_command(message: bytes, mqtt_client):
    """Processa comandos vindos do canal Redis e publica no MQTT."""
    comando = json.loads(message.decode())
    esp_id = comando.get("identificador") or 'c8f09eec0e78'
    if comando["comando"] == "setpoint":
        mqtt_client.publish('setpoint', str(comando["valor"]))
    elif comando["comando"] == "motor":
        mqtt_client.publish(f"esp32/{esp_id}/atuadores/{comando['motor']}", comando["acao"])
