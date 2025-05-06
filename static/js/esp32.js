  // ─── seus objetos globais ──────────────────────────────────────────
  const tempData = {
    labels: [],
    datasets: [{
      label: 'Temperatura (°C)',
      data: [],
      tension: 0.3,
      borderWidth: 2,
      fill: false,
      pointRadius: 0,
      pointHoverRadius: 0,
    }]
  };
  let tempChart;
  let chartRangeMs = null;     // intervalo ativo em ms (null = “Tudo”)
  const statusTimeouts = {};
  let socket;                  // para o WS

  // ─── inicialização do Chart.js ────────────────────────────────────
  function initChart() {
    const ctx = document.getElementById('chart-temperature').getContext('2d');
    tempChart = new Chart(ctx, {
      type: 'line',
      data: tempData,
      options: {
        scales: {
          x: {
            type: 'time',
            time: {
              tooltipFormat: 'HH:mm:ss',
              unit: 'second',
              displayFormats: { second: 'HH:mm:ss' }
            }
          },
          y: {
            title: { display: true, text: '°C' },
            suggestedMin: 0,
            suggestedMax: 50
          }
        }
      }
    });
  }

  // ─── ms por intervalo ───────────────────────────────────────────────
  function msPorRange(range) {
    switch(range) {
      case '1m':  return 1 * 60   * 1000;
      case '15m': return 15 * 60  * 1000;
      case '1h':  return 60 * 60  * 1000;
      case '1d':  return 24 * 60  * 60 * 1000;
      case '1M':  return 30 * 24  * 60 * 60 * 1000;
      default:    return null;
    }
  }

  // ─── carrega histórico via REST ────────────────────────────────────
  async function carregarHistorico(range) {
    const agora = Date.now();
    const ms = msPorRange(range);
  
    // Monta a URL de forma clara, garantindo barra final e query string correta
    let url = '/api/medicoes/historico/?tipo=temp_termistor';
    if (ms !== null) {
      const fromISO = new Date(agora - ms).toISOString();
      const toISO   = new Date(agora).toISOString();
  
      url += `&from=${fromISO}&to=${toISO}`;
      chartRangeMs = ms;
    } else {
      // “Tudo”
      chartRangeMs = null;
    }
  
    // Debug opcional para ver qual URL está sendo chamada
    console.log('Buscando histórico em:', url);
  
    const res = await fetch(url);
    if (!res.ok) {
      console.error('Erro ao buscar histórico', res.status);
      return;
    }
    const dados = await res.json();
  
    // popula o gráfico
    tempData.labels           = dados.map(d => new Date(d.timestamp));
    tempData.datasets[0].data = dados.map(d => Number(d.valor));
    tempChart.update();
  
    // aplica janela (se não for “Tudo”)
    applyTimeWindow(agora);
  }

  // ─── aplica min/max ao chart ───────────────────────────────────────
  function applyTimeWindow(timestampMs) {
    if (chartRangeMs !== null) {
      tempChart.options.scales.x.min = timestampMs - chartRangeMs;
      tempChart.options.scales.x.max = timestampMs;
    } else {
      delete tempChart.options.scales.x.min;
      delete tempChart.options.scales.x.max;
    }
    tempChart.update();
  }

  // ─── abre o WebSocket (chamada única) ──────────────────────────────
  function initWebSocket() {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    socket = new WebSocket(`${proto}://${window.location.host}/ws/esp32/status/`);
    socket.onopen    = () => console.log('WS aberto');
    socket.onclose   = () => console.log('WS fechado');
    socket.onmessage = e => {
      const data = JSON.parse(e.data);
      atualizarCard(data);
      atualizarStatus(data);
      atualizarGrafico(data);
    };
  }

  // ─── muda o intervalo de visualização ──────────────────────────────
  function setTimeRange(range) {
    carregarHistorico(range);
  }

  // ─── manipulações de DOM já existentes ─────────────────────────────
  function atualizarCard({ tipo, valor }) {
    const card = document.getElementById(`card-${tipo}`);
    if (!card) return;
    const unidades = {
      temperature: '°C',
      umidade_ambiente: '%',
      luminosidade: 'lux',
      controlador: '',
      temp_termistor: '',
      erro: ''
    };
    card.textContent = `${valor} ${unidades[tipo]}`;
  }

  function atualizarStatus({ identificador }) {
    const el = document.getElementById(`status-${identificador}`);
    if (!el) return;
    el.innerHTML = `<span class="text-success">🟢 Online</span>`;
    clearTimeout(statusTimeouts[identificador]);
    statusTimeouts[identificador] = setTimeout(() => {
      el.innerHTML = `<span class="text-danger">🔴 Offline</span>`;
    }, 15000);
  }

  // ─── atualiza só um ponto e move a janela ─────────────────────────
  function atualizarGrafico({ tipo, valor, timestamp }) {
    if (tipo.toLowerCase() !== 'temp_termistor') return;
    const time = new Date(timestamp);
    const num = Number(valor);
    if (isNaN(num)) return;

    tempData.labels.push(time);
    tempData.datasets[0].data.push(num);

    // mantém no máximo 500 pontos
    if (tempData.labels.length > 500) {
      tempData.labels.shift();
      tempData.datasets[0].data.shift();
    }

    if (chartRangeMs !== null) {
      applyTimeWindow(time.getTime());
    } else {
      tempChart.update();
    }
  }

  // ─── inicialização geral ───────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    initChart();
    initWebSocket();
    // já carrega 1 hora ao abrir
    carregarHistorico('1h');

    // exemplo: botão de setpoint continua igual
    document.getElementById('btn-setpoint')
      .addEventListener('click', () => {
        const sp = document.getElementById('input-sp').value;
        socket.send(JSON.stringify({ comando: 'setpoint', valor: sp }));
      });
  });
