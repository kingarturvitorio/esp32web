// device_status.js
document.addEventListener('DOMContentLoaded', () => {
  const API_URL = 'api/status-dispositivos/';  // ajuste se necessário
  let devices = {};  // vai guardar { ident: { status, last_ping: Date } }

  // Formata um delta (segundos) para HH:MM:SS
  function fmtDelta(totalSecs) {
    const h = Math.floor(totalSecs/3600).toString().padStart(2,'0');
    const m = Math.floor((totalSecs%3600)/60).toString().padStart(2,'0');
    const s = Math.floor(totalSecs%60).toString().padStart(2,'0');
    return `${h}:${m}:${s}`;
  }

  // Busca status e timestamps do servidor
  async function fetchStatus() {
    try {
      const resp = await fetch(API_URL);
      const data = await resp.json();
      // data: { ident: {status, last_ping} }
      for (const ident in data) {
        const info = data[ident];
        devices[ident] = {
          status: info.status,
          last_ping: info.last_ping ? new Date(info.last_ping) : null
        };
      }
      // após atualizar devices, reflita no DOM imediatamente:
      updateDOM();
    } catch (e) {
      console.error('Erro ao buscar status:', e);
    }
  }

  // Atualiza badges e timers no DOM
  function updateDOM() {
    document.querySelectorAll('.device-card').forEach(card => {
      const ident = card.dataset.ident;
      const info  = devices[ident];
      if (!info) return;
      // badge
      const badge = card.querySelector('.status-badge');
      badge.textContent = info.status === 'online'
        ? '🟢 Online'
        : '🔴 Offline';
      badge.classList.toggle('bg-success', info.status==='online');
      badge.classList.toggle('bg-danger',  info.status!=='online');

      // timer
      const timerEl = card.querySelector('.timer');
      if (info.status === 'online' && info.last_ping) {
        const deltaSecs = (Date.now() - info.last_ping.getTime()) / 1000;
        timerEl.textContent = fmtDelta(deltaSecs);
      } else {
        timerEl.textContent = '--:--:--';
      }
    });
  }

  // Inicia tudo
  fetchStatus();                      // primeira chamada
  setInterval(fetchStatus, 30000);    // atualiza do servidor a cada 30s
  setInterval(updateDOM, 1000);       // atualiza timers a cada 1s
});
