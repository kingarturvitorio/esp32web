import os, json, threading, logging, logging.config
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

import redis
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.rest import ApiException

from controle_acesso.models import Cartao, EventoAcesso
from esp32mqtt.models import Dispositivo, Medicao, GpsFix

from django.contrib.gis.geos import Point   # <-- NECESSÁRIO p/ salvar no PostGIS

class Command(BaseCommand):
    help = "MQTT + Redis consumer"

    def handle(self, *args, **kwargs):
        # logging
        if hasattr(settings, "LOGGING"):
            logging.config.dictConfig(settings.LOGGING)
        logger = logging.getLogger("mqtt_consumer")

        # ---- Influx ----
        INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
        INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "supersecrettoken")
        INFLUX_ORG = os.getenv("INFLUX_ORG", "myorg")
        INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "mybucket")

        influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        write_api = influx.write_api()

        # ---- Redis (pub/sub de comandos) ----
        redis_host = os.getenv("REDIS_HOST", "redis")   # nome do serviço no compose
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db   = int(os.getenv("REDIS_DB", "0"))

        r = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db)
        pubsub = r.pubsub()

        # ---- Channel layer (use settings) ----
        layer = get_channel_layer()  # pega config do CHANNEL_LAYERS

        # ---- MQTT ----
        mqtt_host = os.getenv("MQTT_HOST", "mosquitto")  # serviço do compose
        mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        mqtt_user = os.getenv("MQTT_USER", "")
        mqtt_pass = os.getenv("MQTT_PASS", "")

        def on_connect(client, userdata, flags, rc):
            print(f"🟢 MQTT conectado rc={rc}")
            client.subscribe("esp32/#")

        def on_message(client, userdata, msg):
            topic = msg.topic
            if topic.endswith("/atuadores/2"):
                return
            try:
                parts = topic.split("/")
                # esp32/{identificador}/{tipo}
                _, identificador, tipo = parts[0], parts[1], parts[2]
                payload = msg.payload.decode()
                ts = timezone.now()

                disp = Dispositivo.objects.get(identificador=identificador)
                # LWT atualiza presença
                if tipo == "lwt":
                    if payload == "online": disp.marcar_ping(ts)
                    else: disp.marcar_offline(ts)
                    return

                # ping geral
                disp.marcar_ping(ts)
                
                ws_data = None  # vamos preencher e mandar UMA vez no final

                if tipo == "rfid":
                    try:
                        cartao = Cartao.objects.select_related("usuario").get(uid=payload, ativo=True)
                        autorizado = cartao.usuario.is_active
                    except Cartao.DoesNotExist:
                        cartao, autorizado = None, False
                    EventoAcesso.objects.create(cartao=cartao, dispositivo=identificador, autorizado=autorizado)
                    client.publish(f"esp32/{identificador}/atuadores/2", "on" if autorizado else "off")
                else:
                    # sensores numéricos
                    try:
                        valor = float(payload)
                        Medicao.objects.create(
                            dispositivo=disp, tipo=tipo, valor=valor, timestamp=ts
                        )
                        p = Point("medicao").tag("dispositivo", identificador).tag("tipo", tipo) \
                                .field("valor", valor).time(ts, WritePrecision.NS)
                        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
                    except ApiException as e:
                        logger.warning("Erro InfluxDB: %s", e)
                    except ValueError:
                        pass
                
                if tipo == "gps":
                    data = json.loads(payload)
                    lat = float(data["lat"])
                    lon = float(data["lon"])
                    alt = float(data.get("alt")) if data.get("alt") is not None else None
                    sats = int(data.get("sats")) if data.get("sats") is not None else None
                    hdop = float(data.get("hdop")) if data.get("hdop") is not None else None
                    tsd  = int(data.get("ts")) if data.get("ts") is not None else None

                    # IMPORTANTE: GeoDjango espera (x=lon, y=lat)
                    GpsFix.objects.create(
                        ident=identificador,
                        location=Point(lon, lat, srid=4326),
                        alt=alt, sats=sats, hdop=hdop, ts_device=tsd
                    )
                    return

                # broadcast WS
                async_to_sync(layer.group_send)("esp32_status", {
                    "type": "send_status",
                    "data": {
                        "identificador": identificador,
                        "tipo": tipo,
                        "valor": payload,
                        "timestamp": ts.isoformat(),
                    }
                })

            except Exception:
                logger.exception("Erro no on_message")

        def redis_listener():
            pubsub.subscribe("comandos_esp32")
            print("📡 Escutando Redis canal 'comandos_esp32'…")
            for m in pubsub.listen():
                if m["type"] != "message":
                    continue
                try:
                    comando = json.loads(m["data"].decode())
                    ident = comando.get("identificador")
                    if comando.get("comando") == "setpoint":
                        client.publish("setpoint", str(comando["valor"]))
                    # adicione outros comandos se necessário
                except Exception as e:
                    print("❌ Erro comandos Redis:", e)

        # inicia MQTT
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        if mqtt_user:
            client.username_pw_set(mqtt_user, mqtt_pass)
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(mqtt_host, mqtt_port, keepalive=60)

        threading.Thread(target=redis_listener, daemon=True).start()

        print("🔄 Aguardando mensagens MQTT…")
        client.loop_forever()
