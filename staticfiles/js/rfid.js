// rfid.js
document.addEventListener('DOMContentLoaded', () => {
  const ws = new WebSocket(
    (location.protocol === "https:" ? "wss" : "ws")
    + "://" + location.host
    + "/ws/esp32/status/"
  );

  ws.onmessage = e => {
    const d = JSON.parse(e.data);
    if (d.tipo === "rfid") {
      // se quiser redirecionar automaticamente para o create com ?uid=
      // window.location.href = `/acesso/cartoes/add/?uid=${d.valor}`;

      // ou, se estiver no form de edição/criação:
      const uidInput = document.getElementById("id_uid");
      if (uidInput) {
        uidInput.value = d.valor;
      }
    }
  };
});
