import os, json, threading, logging, logging.config
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

import redis
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point as IFXPoint, WritePrecision
from influxdb_client.rest import ApiException

from controle_acesso.models import Cartao, EventoAcesso
from esp32mqtt.models import Dispositivo, Medicao, GpsFix

from django.contrib.gis.geos import Point as GEOSPoint   # <-- NECESSÁRIO p/ salvar no PostGIS

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
                _, identificador, tipo = parts[0], parts[1], parts[2]
                payload = msg.payload.decode()
                ts = timezone.now()

                disp = Dispositivo.objects.get(identificador=identificador)

                # 1) LWT (online/offline) e PING
                if tipo == "lwt":
                    if payload == "online":
                        disp.marcar_ping(ts)
                    else:
                        disp.marcar_offline(ts)
                    # pode fazer um broadcast simples se quiser
                    async_to_sync(layer.group_send)("esp32_status", {
                        "type": "send_status",
                        "data": {"identificador": identificador, "tipo": "lwt", "valor": payload, "timestamp": ts.isoformat()}
                    })
                    return

                # marca presença "viva"
                disp.marcar_ping(ts)

                ws_data = None  # vamos preencher e mandar UMA vez no final

                # 2) GPS (trate ANTES dos sensores numéricos)
                if tipo == "gps":
                    data = json.loads(payload)
                    lat  = float(data["lat"])
                    lon  = float(data["lon"])
                    alt  = float(data.get("alt")) if data.get("alt") is not None else None
                    sats = int(data.get("sats"))  if data.get("sats") is not None else None
                    hdop = float(data.get("hdop")) if data.get("hdop") is not None else None
                    tsd  = int(data.get("ts"))    if data.get("ts") is not None else None

                    # salva no PostGIS (x=lon, y=lat)
                    GpsFix.objects.create(
                        ident=identificador,
                        location=GEOSPoint(lon, lat, srid=4326),
                        alt=alt, sats=sats, hdop=hdop, ts_device=tsd
                    )

                    # prepara payload WS específico de GPS
                    ws_data = {
                        "identificador": identificador,
                        "tipo": "gps",
                        "lat": lat,
                        "lon": lon,
                        "alt": alt,
                        "sats": sats,
                        "hdop": hdop,
                        "ts_device": tsd,
                        "created_at": ts.isoformat(),
                    }

                # 3) RFID
                elif tipo == "rfid":
                    try:
                        cartao = Cartao.objects.select_related("usuario").get(uid=payload, ativo=True)
                        autorizado = cartao.usuario.is_active
                    except Cartao.DoesNotExist:
                        cartao, autorizado = None, False

                    EventoAcesso.objects.create(
                        cartao=cartao, dispositivo=identificador, autorizado=autorizado
                    )
                    client.publish(f"esp32/{identificador}/atuadores/2", "on" if autorizado else "off")

                    ws_data = {
                        "identificador": identificador,
                        "tipo": "rfid",
                        "uid": payload,
                        "autorizado": autorizado,
                        "timestamp": ts.isoformat(),
                    }

                # 4) Sensores numéricos (qualquer outro tipo virar float)
                else:
                    valor = None
                    try:
                        valor = float(payload)
                        Medicao.objects.create(
                            dispositivo=disp, tipo=tipo, valor=valor, timestamp=ts
                        )
                        p = (
                            IFXPoint("medicao")
                            .tag("dispositivo", identificador).tag("tipo", tipo)
                            .field("valor", valor).time(ts, WritePrecision.NS)
                        )
                        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
                    except ApiException as e:
                        logger.warning("Erro InfluxDB: %s", e)
                    except ValueError:
                        # não era número: ignore ou trate se quiser
                        pass

                    # debug antes de enviar WS
                    print("WS ->", {
                        "identificador": identificador,
                        "tipo": tipo,
                        "valor": payload,
                        "timestamp": ts.isoformat(),
                    })

                    ws_data = {
                        "identificador": identificador,
                        "tipo": tipo,
                        "valor": payload,  # mantenha string p/ front decidir
                        "timestamp": ts.isoformat(),
                    }

                # 5) SEMPRE: broadcast WS (uma vez por mensagem)
                if ws_data is not None:
                    async_to_sync(layer.group_send)(
                        "esp32_status",
                        {"type": "send_status", "data": ws_data}
                    )

            except Exception:
                logger.exception("Erro no on_message")

        def redis_listener():
            pubsub.subscribe("comandos_esp32")
            print("📡 Escutando Redis canal 'comandos_esp32'…")
            for m in pubsub.listen():
                if m["type"] != "message":
                    continue
                try:
                    raw = m["data"]                      # bytes
                    print("REDIS RX raw ->", raw)
                    comando = json.loads(raw.decode())   # dict
                    print("REDIS RX json ->", comando)

                    ident = (comando.get("identificador") or "").strip()
                    op    = (comando.get("comando") or "").lower()
                    valor = str(comando.get("valor", "")).strip()
                    print(f"CMD op={op!r} valor={valor!r} ident={ident!r}")

                    def norm_bool(v):
                        v = str(v).strip().lower()
                        if v in ("on","1","true","open"):    return "on"
                        if v in ("off","0","false","close"): return "off"
                        return v  # ângulo etc.

                    # confirma conexão MQTT (debug)
                    if not client.is_connected():
                        print("⚠️ MQTT client NÃO conectado (reconectando?)")

                    # callback para confirmar publicação
                    def _on_pub(cli, userdata, mid):
                        print(f"MQTT PUB ACK mid={mid}")

                    client.on_publish = _on_pub

                    if op == "setpoint":
                        rc, mid = client.publish("setpoint", valor, qos=1)
                        print(f"MQTT -> topic=setpoint payload={valor!r} rc={rc} mid={mid}")

                    elif op == "atuador1":
                        v = norm_bool(valor)
                        rc, mid = client.publish("atuadores/1", v, qos=1)
                        print(f"MQTT -> topic=atuadores/1 payload={v!r} rc={rc} mid={mid}")

                    elif op == "atuador2":
                        v = norm_bool(valor)
                        topic = f"esp32/{ident}/atuadores/2" if ident else "atuadores/2"
                        rc, mid = client.publish(topic, v, qos=1)
                        print(f"MQTT -> topic={topic} payload={v!r} rc={rc} mid={mid}")

                    else:
                        print("⚠️ Comando desconhecido:", comando)

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
