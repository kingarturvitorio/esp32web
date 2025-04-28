from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Dispositivo(models.Model):
    nome = models.CharField(max_length=100)
    identificador = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    #campo para verificar o ultimo ping do esp32 para verificar se ele esta conectado
    ultimo_ping = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.nome} ({self.identificador})'
    
    def esta_online(self):
        "Retorna True se o dispositivo enviou dados recentemente"
        if self.ultimo_ping:
            return(timezone.now()-self.ultimo_ping).total_seconds()< 60
        return False

class Medicao(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=50)
    valor = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)