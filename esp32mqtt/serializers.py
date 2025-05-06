from rest_framework import serializers
from .models import Medicao

class MedicaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicao
        fields = ('id', 'dispositivo', 'tipo', 'valor', 'timestamp')
