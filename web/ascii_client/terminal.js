(() => {
  const USER_ID = localStorage.getItem("dnd_user_id") || "player1";
  localStorage.setItem("dnd_user_id", USER_ID);

  const logEl = document.getElementById("log");
  const detailEl = document.getElementById("detail");
  const inputEl = document.getElementById("input");
  const formEl = document.getElementById("input-form");
  const connEl = document.getElementById("conn-status");
  const campaignEl = document.getElementById("campaign-label");

  let ws = null;
  let sessionId = USER_ID;

  function appendLog(text, cls) {
    const line = document.createElement("div");
    if (cls) line.className = cls;
    line.textContent = text;
    logEl.appendChild(line);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function setDetail(frame) {
    if (frame == null || frame === "") return;
    detailEl.textContent = frame;
  }

  function setOnline(online) {
    connEl.textContent = online ? "ONLINE" : "OFFLINE";
    connEl.className = online ? "status-online" : "status-offline";
  }

  async function refreshStatus() {
    try {
      const res = await fetch("/api/status");
      if (!res.ok) return;
      const data = await res.json();
      if (data.campaign_loaded) {
        const info = data.campaign_info || {};
        campaignEl.textContent = `${data.campaign_loaded} | act ${info.act ?? "?"} | ${info.location ?? ""}`;
      } else {
        campaignEl.textContent = "no campaign";
      }
    } catch (_) {
      /* ignore */
    }
  }

  function connectWs() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${location.host}/ws/${encodeURIComponent(USER_ID)}`;
    ws = new WebSocket(url);

    ws.onopen = () => {
      setOnline(true);
      appendLog("[system] WebSocket connected", "log-system");
    };

    ws.onclose = () => {
      setOnline(false);
      appendLog("[system] WebSocket disconnected — retrying...", "log-system");
      setTimeout(connectWs, 3000);
    };

    ws.onerror = () => {
      setOnline(false);
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        const type = msg.type || "dm";
        if (type === "session_change" && msg.session_id) {
          sessionId = msg.session_id;
        }
        if (msg.campaign_info && msg.campaign_info.name) {
          campaignEl.textContent = `${msg.campaign_info.name} | act ${msg.campaign_info.act ?? "?"} | ${msg.campaign_info.location ?? ""}`;
        }
        const body = msg.message || msg.content || JSON.stringify(msg);
        if (type === "system" || type === "session_change") {
          appendLog(`[system] ${body}`, "log-system");
        } else if (type === "user") {
          appendLog(`You: ${body}`, "log-user");
        } else {
          appendLog(`DM: ${body}`, "log-dm");
        }
        if (msg.detail_frame) setDetail(msg.detail_frame);
      } catch (_) {
        appendLog(String(ev.data), "log-dm");
      }
    };
  }

  async function runCommand(command) {
    appendLog(`> ${command}`, "log-user");
    try {
      const res = await fetch("/api/terminal/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          command,
          user_id: USER_ID,
          session_id: sessionId,
        }),
      });
      const data = await res.json();
      const lines = data.log_lines || [data.detail || data.message || "OK"];
      const cls = data.ok === false ? "log-error" : "log-ok";
      for (const line of lines) appendLog(line, cls);
      if (data.detail_frame) setDetail(data.detail_frame);
      await refreshStatus();
    } catch (err) {
      appendLog(`ERROR: ${err}`, "log-error");
    }
  }

  function sendChat(message) {
    appendLog(`You: ${message}`, "log-user");
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      appendLog("ERROR: WebSocket offline", "log-error");
      return;
    }
    ws.send(JSON.stringify({ type: "chat", message }));
  }

  formEl.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = inputEl.value.trim();
    if (!text) return;
    inputEl.value = "";
    if (text.startsWith("/")) {
      runCommand(text);
    } else {
      sendChat(text);
    }
  });

  appendLog("ASCII Terminal ready. Type /help or chat with the DM.", "log-system");
  refreshStatus();
  connectWs();
  runCommand("/help");
  inputEl.focus();
})();
