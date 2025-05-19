from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Cartao(models.Model):
    uid     = models.CharField(max_length=32, unique=True)
    usuario = models.ForeignKey(User,   on_delete=models.CASCADE)
    ativo   = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.uid} → {self.usuario}"

class EventoAcesso(models.Model):
    cartao       = models.ForeignKey(Cartao,        on_delete=models.SET_NULL, null=True)
    timestamp    = models.DateTimeField(auto_now_add=True)
    autorizado   = models.BooleanField()
    dispositivo  = models.CharField(max_length=50)

    def __str__(self):
        status = "OK" if self.autorizado else "NEGADO"
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.dispositivo} – {self.cartao} → {status}"
