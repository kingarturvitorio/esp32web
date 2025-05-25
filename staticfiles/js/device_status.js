// static/js/device_status_socket.js

document.addEventListener('DOMContentLoaded', () => {
  const ws = new WebSocket(
    (location.protocol === "https:" ? "wss" : "ws")
    + "://" + location.host
    + "/ws/esp32/status/"
  );

  ws.onopen = () => console.log("WebSocket conectado em", ws.url);
  ws.onclose = () => console.log("WebSocket desconectado");
  ws.onerror = e => console.error("WebSocket erro", e);

  ws.onmessage = e => {
    let msg;
    try {
      msg = JSON.parse(e.data);
    } catch {
      console.warn("JSON inválido:", e.data);
      return;
    }

    const ident = msg.identificador;
    const tipo  = msg.tipo;
    const valor = msg.valor;

    // apenas reaja a 'lwt' (online/offline) ou 'status' (uptime)
    if (tipo !== "lwt" && tipo !== "status") {
      return;
    }

    // localiza o card e seus elementos
    const card  = document.querySelector(`.device-card[data-ident="${ident}"]`);
    const badge = card && card.querySelector(".status-badge");
    const timer = document.getElementById(`timer-${ident}`);
    if (!card || !badge || !timer) {
      console.warn("Elementos não encontrados para", ident);
      return;
    }

    if (tipo === "lwt") {
      // LWT: payload é "online" ou "offline"
      const isOnline = (valor === "online");
      badge.textContent = isOnline ? "🟢 Online" : "🔴 Offline";
      badge.classList.toggle("bg-success", isOnline);
      badge.classList.toggle("bg-danger", !isOnline);

      // se offline, zera o timer
      if (!isOnline) {
        timer.textContent = "--:--:--";
      }
    }

    else if (tipo === "status") {
      // Status: payload é JSON string com { uptime: <segundos>, ... }
      let info;
      try {
        info = JSON.parse(valor);
      } catch {
        console.warn("JSON de status inválido:", valor);
        return;
      }
      const secs = Number(info.uptime) || 0;
      const h = String(Math.floor(secs/3600)).padStart(2,'0');
      const m = String(Math.floor((secs%3600)/60)).padStart(2,'0');
      const s = String(secs%60).padStart(2,'0');
      timer.textContent = `${h}:${m}:${s}`;
    }
  };
});
