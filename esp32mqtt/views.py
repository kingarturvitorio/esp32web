from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from . models import Dispositivo, Medicao
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .serializers import MedicaoSerializer
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.dateparse import parse_datetime
from django.http import StreamingHttpResponse
from esp32mqtt.models import GpsFix
import json
from django.shortcuts import render

class DispositivoCreateView(LoginRequiredMixin, CreateView):
    model = Dispositivo
    fields = ['nome', 'identificador', 'descricao']
    template_name = 'criar_dispositivos.html'
    success_url = reverse_lazy('lista-dispositivos')

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)

class DispositivoListView(LoginRequiredMixin, ListView):
    model = Dispositivo
    template_name = 'listar_dispositivos.html'

    def get_queryset(self):
        return Dispositivo.objects.filter(usuario=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()

        for d in ctx['object_list']:
            # calcula sessão atual
            sessão = 0
            if d.esta_online() and d.ultima_entrada_online:
                sessão = (now - d.ultima_entrada_online).total_seconds()
            total = d.tempo_online_acumulado + int(sessão)
            h = total // 3600
            m = (total % 3600) // 60
            s = total % 60
            # anexa no próprio objeto pra usar no template
            d.uptime_str = f"{h:02d}:{m:02d}:{s:02d}"

        return ctx
    
class DispositivoUpdateView(LoginRequiredMixin, UpdateView):
    model = Dispositivo
    fields = ['nome', 'identificador', 'descricao']
    template_name = 'editar_dispositivos.html'
    success_url = reverse_lazy('lista-dispositivos')

class DispositivoDeleteView(LoginRequiredMixin, DeleteView):
    model = Dispositivo
    template_name = 'excluir_dispositivos.html'
    success_url = reverse_lazy('lista-dispositivos')

class DispositivoDetailView(DetailView):
    model = Dispositivo
    template_name = 'detalhe_dispositivos.html'

##view para retornar via ajax de forma automatica na tela
def status_dispositivos(request):
    now = timezone.now()
    data = {}

    for d in Dispositivo.objects.all():
        # se estiver online, some a sessão atual
        sessao_atual = 0
        if d.esta_online() and d.ultima_entrada_online:
            sessao_atual = (now - d.ultima_entrada_online).total_seconds()

        total_secs = d.tempo_online_acumulado + int(sessao_atual)

        data[d.identificador] = {
            "status":    "online" if d.esta_online() else "offline",
            "uptime":    total_secs,
            "last_ping": d.ultimo_ping.isoformat() if d.ultimo_ping else None
        }

    return JsonResponse(data)

class SistemaMonitoramentoView(LoginRequiredMixin, ListView):
    model = Dispositivo
    template_name = 'sistema_monitoramento.html'

# class MedicaoViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = Medicao.objects.all().order_by('timestamp')
#     serializer_class = MedicaoSerializer

#     @action(detail=False, methods=['get'])
#     def historico(self, request):
#         # espera query params: ?tipo=temp_termistor&from=...&to=...
#         tipo = request.query_params.get('tipo')
#         since = parse_datetime(request.query_params.get('from'))
#         until = parse_datetime(request.query_params.get('to'))

#         qs = self.queryset
#         if tipo:
#             qs = qs.filter(tipo=tipo)
#         if since:
#             qs = qs.filter(timestamp__gte=since)
#         if until:
#             qs = qs.filter(timestamp__lte=until)

#         serializer = MedicaoSerializer(qs, many=True)
#         return Response(serializer.data)

class MedicaoViewSet(viewsets.ReadOnlyModelViewSet):
    ##fiz dessa forma para tratar os dados que chegam no frontend para não carregar tudo de uma vez
    # e sobrecarregar para o usuário, sendo assim, só mostra o periodo de tempo informado e os
    # dados carregam mais rapidamente.
    queryset = Medicao.objects.all().order_by('timestamp')
    serializer_class = MedicaoSerializer

    def _parse_iso(self, s):
        """
        Corrige o 'Z' final para '+00:00' (UTC) antes de usar parse_datetime.
        Retorna None se parse_datetime falhar.
        """
        if not s:
            return None
        # Exemplo de entrada: '2025-05-20T14:00:00.000Z'
        if s.endswith('Z'):
            # transforma em '2025-05-20T14:00:00.000+00:00'
            s = s[:-1] + '+00:00'
        return parse_datetime(s)

    @action(detail=False, methods=['get'])
    def historico(self, request):
        tipo  = request.query_params.get('tipo')
        raw_f = request.query_params.get('from')
        raw_t = request.query_params.get('to')

        since = self._parse_iso(raw_f)
        until = self._parse_iso(raw_t)

        qs = self.queryset
        if tipo:
            qs = qs.filter(tipo=tipo)

        if since:
            qs = qs.filter(timestamp__gte=since)
        if until:
            qs = qs.filter(timestamp__lte=until)

        # opcional: paginação automática, para não trazer tudo de uma vez
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

def esp32_events(request):
    def event_stream():
        # subscribe no Redis ou Channels aqui
        while True:
            msg = redis_client.blpop('esp32_status')[1]
            yield f"data: {msg.decode()}\n\n"
    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')


def gps_latest_geojson(request):
    """
    Retorna um FeatureCollection com o último ponto de cada ident.
    Usa DISTINCT ON (Postgres): order_by('ident','-created_at').distinct('ident')
    """
    qs = (GpsFix.objects
          .order_by('ident', '-created_at')  # chave + mais recente
          .distinct('ident'))

    features = []
    for row in qs:
        geom = json.loads(row.location.geojson)  # {"type":"Point","coordinates":[lon,lat]}
        props = {
            "ident": row.ident,
            "alt": row.alt,
            "sats": row.sats,
            "hdop": row.hdop,
            "ts_device": row.ts_device,
            "created_at": row.created_at.isoformat(),
        }
        features.append({"type": "Feature", "geometry": geom, "properties": props})

    return JsonResponse({"type": "FeatureCollection", "features": features})

def mapa_gps(request):
    return render(request, "mapa.html")