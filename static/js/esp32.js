// conecta o WebSocket
const socket = new WebSocket(`ws://${window.location.host}/ws/esp32/status/`);
const statusTimeouts = {};
socket.onmessage = onMessageESP;

// registra eventos de DOM após carregamento
window.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-setpoint')
          .addEventListener('click', enviarSP);
});

function onMessageESP(event) {
  const data = JSON.parse(event.data);
  atualizarCard(data);
  atualizarStatus(data);
  logMQTT(data);
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
    // status: '',
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

// function logMQTT({ timestamp, identificador, status }) {
//   const mensagensDiv = document.getElementById('mensagens-mqtt');
//   const nova = document.createElement('div');
//   nova.innerText = `[${timestamp}] ${identificador}: ${status}`;
//   mensagensDiv.prepend(nova);
// }

function enviarSP() {
  
  const sp = document.getElementById('input-sp').value;
  console.log("📥 Mensagem WebSocket recebida:", sp);
  socket.send(JSON.stringify({ comando: 'setpoint', valor: sp }));
}