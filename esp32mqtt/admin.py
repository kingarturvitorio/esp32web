from django.contrib import admin
from .models import Dispositivo, Medicao, GpsFix

admin.site.register(Dispositivo)
admin.site.register(Medicao)
admin.site.register(GpsFix)

