from django.contrib import admin
from .models import Estado, Cidade, Campus, Servidor, Status, Situacao, Classe, Comprovante, Validacao, Campo, Atividade
# Register your models here.

admin.site.register(Estado)
admin.site.register(Cidade)
admin.site.register(Campus)
admin.site.register(Servidor)
admin.site.register(Status)
admin.site.register(Situacao)
admin.site.register(Classe)
admin.site.register(Comprovante)
admin.site.register(Campo)
admin.site.register(Atividade)
admin.site.register(Validacao)

