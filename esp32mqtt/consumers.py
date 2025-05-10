import json
from channels.generic.websocket import AsyncWebsocketConsumer
import redis
from esp32mqtt.models import Dispositivo

redis_client = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)

class StatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("esp32_status", self.channel_name)
        await self.accept()
        #print("🟢 WebSocket conectado:", self.channel_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("esp32_status", self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        #print("📥 RECEBIDO do navegador:", data)

        # Exemplo de comando: { comando: "setpoint", valor: 30 }
        redis_client.publish("comandos_esp32", json.dumps(data))

    async def send_status(self, event):
        #print("📡 MENSAGEM RECEBIDA NO CONSUMER:", event["data"])
        await self.send(text_data=json.dumps(event["data"]))
