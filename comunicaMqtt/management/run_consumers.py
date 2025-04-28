from django.core.management.base import BaseCommand
from comunicaMqtt.consumers.mqtt_client import run_mqtt

class Command(BaseCommand):
    help = "Inicia o consumidor MQTT + listener Redis"

    def handle(self, *args, **options):
        run_mqtt()