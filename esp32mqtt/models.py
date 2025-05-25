from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Dispositivo(models.Model):
    nome                   = models.CharField(max_length=100)
    identificador          = models.CharField(max_length=100, unique=True)
    descricao              = models.TextField(blank=True)
    usuario                = models.ForeignKey(User, on_delete=models.CASCADE)
    ultimo_ping            = models.DateTimeField(null=True, blank=True)
    criado_em              = models.DateTimeField(auto_now_add=True)

    # novos campos
    tempo_online_acumulado = models.IntegerField(default=0)
    ultima_entrada_online  = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.nome} ({self.identificador})'

    def esta_online(self):
        if not self.ultimo_ping:
            return False
        return (timezone.now() - self.ultimo_ping).total_seconds() < 60

    def marcar_ping(self, agora=None):
        agora = agora or timezone.now()
        if self.ultima_entrada_online:
            # Já está online: só atualiza o último ping
            self.ultimo_ping = agora
            self.save(update_fields=['ultimo_ping'])
        else:
            # Veio de offline → entrou em online
            self.ultima_entrada_online = agora
            self.ultimo_ping = agora
            self.save(update_fields=['ultima_entrada_online', 'ultimo_ping'])

    def marcar_offline(self, agora=None):
        agora = agora or timezone.now()
        if self.ultima_entrada_online:
            # Calcula duração da sessão e acumula
            duracao = (agora - self.ultima_entrada_online).total_seconds()
            self.tempo_online_acumulado += int(duracao)
            self.ultima_entrada_online = None
            self.save(update_fields=['tempo_online_acumulado', 'ultima_entrada_online'])

class Medicao(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=50)
    valor = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)