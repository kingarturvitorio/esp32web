// dados do gráfico & escopos globais
const tempData = {
  labels: [],
  datasets: [{
    label: 'Temperatura (°C)',
    data: [],
    tension: 0.3,
    borderWidth: 2,
    fill: false,
        // **–– essas duas linhas desativam os bolinhas ––**
    pointRadius: 0,
    pointHoverRadius: 0,
  }]
};

let tempChart;
let chartRangeMs = null;     // intervalo ativo em ms (null = “Tudo”)
const statusTimeouts = {};

// cria o gráfico e o socket
window.addEventListener('DOMContentLoaded', () => {
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

  // WebSocket
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${proto}://${window.location.host}/ws/esp32/status/`);
  socket.onopen    = () => console.log('WS aberto');
  socket.onclose   = () => console.log('WS fechado');
  socket.onmessage = e => {
    const data = JSON.parse(e.data);
    atualizarCard(data);
    atualizarStatus(data);
    atualizarGrafico(data);
  };

  // Setpoint
  document.getElementById('btn-setpoint')
    .addEventListener('click', () => {
      const sp = document.getElementById('input-sp').value;
      socket.send(JSON.stringify({ comando: 'setpoint', valor: sp }));
    });
});

// muda o intervalo e já aplica num “frame zero”
function setTimeRange(range) {
  const now = Date.now();
  switch (range) {
    case '1m': chartRangeMs = 1 * 60 * 1000; break;
    case '15m': chartRangeMs = 15 * 60 * 1000; break;
    case '1h': chartRangeMs = 60 * 60 * 1000; break;
    case '1d': chartRangeMs = 24 * 60 * 60 * 1000; break;
    case '1M': chartRangeMs = 30 * 24 * 60 * 60 * 1000; break;
    default: chartRangeMs = null;
  }
  applyTimeWindow(now);
}


// aplica min/max ao chart
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

// atualiza só um ponto e move a janela
function atualizarGrafico({ tipo, valor, timestamp }) {
  if (tipo.toLowerCase() !== 'temp_termistor') return;

  // converte o timestamp que vem como ISO-string
  const time = (typeof timestamp === 'string')
    ? new Date(timestamp)
    : (typeof timestamp === 'number')
      ? new Date(timestamp * 1000)
      : new Date();

  const num = Number(valor);
  if (isNaN(num)) return;

  tempData.labels.push(time);
  tempData.datasets[0].data.push(num);

  if (tempData.labels.length > 500) {
    tempData.labels.shift();
    tempData.datasets[0].data.shift();
  }

  // se o usuário escolheu um intervalo, move a janela pra sempre “agora”
  if (chartRangeMs !== null) {
    applyTimeWindow(time.getTime());
  } else {
    tempChart.update();
  }
}
