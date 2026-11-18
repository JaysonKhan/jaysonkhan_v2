// Voice agent demo page (/<lang>/demos/voice-agent/): microphone -> relay, relay audio -> speakers,
// and the live view. Config (call token, WebSocket URL, worklet URL, 4-language strings) comes from
// the server-rendered #voice-config JSON, so no URL or string is hardcoded here.
(function () {
  "use strict";

  const configEl = document.getElementById("voice-config");
  if (!configEl) return;
  const config = JSON.parse(configEl.textContent);
  const T = config.text;
  const $ = (id) => document.getElementById(id);

  let call = null; // { ws, ctx, stream, player, ready, failed, timer }
  const turns = [];
  const pendingUserLines = [];
  const agentLines = new Map();

  // ---------- call lifecycle ----------

  function wsUrl() {
    const base =
      config.wsUrl ||
      `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/demos/voice-agent/ws`;
    return `${base}?token=${encodeURIComponent(config.token)}`;
  }

  async function startCall() {
    hideError();
    setState("connecting");
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
      });
    } catch {
      showError(T.errors.mic_blocked);
      setState("idle");
      return;
    }
    const ctx = new AudioContext({ sampleRate: 24000 });
    await ctx.audioWorklet.addModule(config.workletUrl);
    const capture = new AudioWorkletNode(ctx, "capture", {
      numberOfOutputs: 0,
    });
    const player = new AudioWorkletNode(ctx, "playback", {
      outputChannelCount: [1],
    });
    ctx.createMediaStreamSource(stream).connect(capture);
    player.connect(ctx.destination);

    const ws = new WebSocket(wsUrl());
    ws.binaryType = "arraybuffer";
    call = { ws, ctx, stream, player, ready: false, failed: false, timer: 0 };

    capture.port.onmessage = ({ data }) => {
      if (ws.readyState === WebSocket.OPEN) ws.send(data.pcm);
      floor.level("you", data.rms);
    };
    player.port.onmessage = ({ data }) => {
      if (data.type === "level") floor.level("agent", data.rms);
      else if (data.type === "stopped")
        send({
          type: "playback_stopped",
          item_id: data.itemId,
          played_ms: data.playedMs,
        });
      else if (data.type === "drained")
        send({
          type: "playback_done",
          item_id: data.itemId,
          played_ms: data.playedMs,
        });
    };
    ws.onmessage = ({ data }) => {
      if (typeof data === "string") onServerEvent(JSON.parse(data));
      else player.port.postMessage({ type: "chunk", pcm: data }, [data]);
    };
    ws.onclose = () => {
      if (call?.ws !== ws) return;
      if (!call.failed)
        showError(call.ready ? T.errors.closed : T.errors.unavailable);
      endCall();
    };

    setToggle(true);
    floor.run();
  }

  function endCall() {
    if (!call) return;
    const { ws, ctx, stream, timer } = call;
    call = null;
    clearInterval(timer);
    ws.close();
    stream.getTracks().forEach((track) => track.stop());
    ctx.close();
    setState("ended");
    setToggle(false);
    $("voice-timer").hidden = true;
    floor.stop();
  }

  function send(event) {
    if (call?.ws.readyState === WebSocket.OPEN)
      call.ws.send(JSON.stringify(event));
  }

  // ---------- server events ----------

  function onServerEvent(event) {
    switch (event.type) {
      case "ready":
        call.ready = true;
        if (event.max_seconds) startTimer(event.max_seconds);
        break;
      case "state":
        setState(event.state);
        if (event.state === "user_speaking") addUserLine();
        break;
      case "user_text":
        fillUserLine(event.text);
        break;
      case "agent_audio_start":
        call.player.port.postMessage({ type: "start", itemId: event.item_id });
        agentLines.set(event.item_id, addLine("agent", T.agent, ""));
        break;
      case "agent_text":
        appendAgentText(event.item_id, event.delta);
        break;
      case "agent_audio_done":
        call.player.port.postMessage({ type: "done" });
        break;
      case "interrupt": // the user talked over the agent: silence it now, the relay truncates
        call.player.port.postMessage({ type: "stop" });
        markCut(agentLines.get(event.item_id));
        setState("interrupted");
        floor.mark({ kind: "cut", t: performance.now() });
        break;
      case "barge_in":
        addBargeInNote(event);
        break;
      case "turn":
        addTurn(event);
        floor.mark({
          kind: "latency",
          t0: performance.now() - event.latency_ms,
          t1: performance.now(),
          ms: event.latency_ms,
        });
        break;
      case "error":
        if (event.code === "upstream") {
          console.warn("Realtime API:", event.message); // non-fatal; the call goes on
          break;
        }
        call.failed = true;
        showError(
          (T.errors[event.code] || T.errors.unavailable).replace(
            "{min}",
            Math.round(config.maxMinutes || 3),
          ),
        );
        break;
    }
  }

  // ---------- page updates ----------

  function setState(state) {
    $("voice-state").dataset.state = state;
    $("voice-state-text").textContent = T[state] || state;
  }

  function setToggle(inCall) {
    $("voice-toggle-text").textContent = inCall ? T.end : T.start;
    $("voice-toggle").classList.toggle("btn-primary", !inCall);
  }

  function startTimer(seconds) {
    const endsAt = performance.now() + seconds * 1000;
    const timer = $("voice-timer");
    timer.hidden = false;
    const tick = () => {
      const left = Math.max(0, Math.ceil((endsAt - performance.now()) / 1000));
      timer.textContent = `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}`;
    };
    tick();
    call.timer = setInterval(tick, 250);
  }

  function showError(message) {
    $("voice-error").textContent = message;
    $("voice-error").hidden = false;
  }

  function hideError() {
    $("voice-error").hidden = true;
  }

  function addLine(cls, who, text) {
    const list = $("voice-transcript");
    list.querySelector(".voice-transcript__empty")?.remove();
    const li = document.createElement("li");
    li.className = `voice-transcript__line voice-transcript__line--${cls}`;
    const label = document.createElement("span");
    label.className = "mono-label";
    label.textContent = who;
    const body = document.createElement("span");
    body.className = "voice-transcript__text";
    body.textContent = text;
    li.append(label, body);
    list.append(li);
    list.scrollTop = list.scrollHeight;
    return li;
  }

  function markCut(li) {
    if (!li || li.querySelector(".voice-transcript__cut")) return;
    const tag = document.createElement("span");
    tag.className = "voice-transcript__cut";
    tag.textContent = T.cut;
    li.querySelector(".mono-label").after(tag);
  }

  function addUserLine() {
    pendingUserLines.push(addLine("you", T.you, "…"));
  }

  function fillUserLine(text) {
    const li = pendingUserLines.shift();
    if (!li) return;
    if (text.trim())
      li.querySelector(".voice-transcript__text").textContent = text.trim();
    else li.remove(); // the detector heard noise, not words
  }

  function appendAgentText(itemId, delta) {
    const li = agentLines.get(itemId);
    if (!li) return;
    li.querySelector(".voice-transcript__text").textContent += delta;
    $("voice-transcript").scrollTop = $("voice-transcript").scrollHeight;
  }

  function addTurn(t) {
    turns.push(t);
    const body = $("voice-turns");
    body.querySelector(".voice-turns__empty")?.remove();
    const row = body.insertRow();
    for (const text of [
      t.turn,
      `${t.latency_ms} ms`,
      `${t.vad_wait_ms} ms`,
      `${t.response_ms} ms`,
    ]) {
      row.insertCell().textContent = text;
    }
    row.cells[1].className = "voice-turns__total";
    const sorted = turns.map((x) => x.latency_ms).sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    const median =
      sorted.length % 2
        ? sorted[mid]
        : Math.round((sorted[mid - 1] + sorted[mid]) / 2);
    const value = document.createElement("strong");
    value.textContent = `${median} ms`;
    $("voice-median").replaceChildren(`${T.median} `, value);
  }

  function addBargeInNote(b) {
    const row = $("voice-turns").insertRow();
    row.className = "voice-turns__note";
    const cell = row.insertCell();
    cell.colSpan = 4;
    cell.textContent = T.barge_in
      .replace("{s}", (b.heard_ms / 1000).toFixed(1))
      .replace("{ms}", b.stop_ms ?? "–");
  }

  // ---------- the floor: who is talking over the last 10 seconds ----------

  const floor = (() => {
    const WINDOW_MS = 10_000;
    const canvas = $("voice-floor");
    const g = canvas.getContext("2d");
    const mono =
      getComputedStyle(document.documentElement)
        .getPropertyValue("--font-mono")
        .trim() || "monospace";
    const colorCache = new Map();
    const levels = { you: [], agent: [] };
    let marks = [];
    let frame = 0;

    // Resolve a design token (oklch / color-mix) to a color the canvas understands.
    function color(token) {
      if (!colorCache.has(token)) {
        const probe = document.createElement("span");
        probe.style.color = `var(${token})`;
        document.body.append(probe);
        colorCache.set(token, getComputedStyle(probe).color);
        probe.remove();
      }
      return colorCache.get(token);
    }

    function level(lane, rms) {
      const db = 20 * Math.log10(Math.max(rms, 1e-6));
      levels[lane].push({
        t: performance.now(),
        v: Math.min(1, Math.max(0, (db + 60) / 50)),
      });
    }

    function mark(m) {
      marks.push(m);
    }

    function label(text, x, y, token, weight = 500) {
      g.font = `${weight} 11px ${mono}`;
      g.fillStyle = color(token);
      g.fillText(text.toUpperCase(), x, y);
    }

    function draw() {
      const dpr = window.devicePixelRatio || 1;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
        canvas.width = w * dpr;
        canvas.height = h * dpr;
      }
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      g.clearRect(0, 0, w, h);
      g.textBaseline = "middle";
      const now = performance.now();
      const left = 76;
      const right = w - 12;
      const x = (t) => left + (right - left) * (1 - (now - t) / WINDOW_MS);
      const lanes = { you: h * 0.27, agent: h * 0.73 };
      const half = h * 0.16;

      label(T.you, 4, lanes.you, "--fg-2");
      label(T.agent, 4, lanes.agent, "--accent-2");
      g.fillStyle = color("--line-2");
      g.fillRect(left, lanes.you, right - left, 1);
      g.fillRect(left, lanes.agent, right - left, 1);

      if (!call && !levels.you.length) {
        g.font = `400 13px ${mono}`;
        g.fillStyle = color("--fg-3");
        g.textAlign = "center";
        const lines = [""]; // wrap to the lane width (long uz/ru/xo copy on phones)
        for (const word of T.floor_empty.split(" ")) {
          const next = lines[lines.length - 1]
            ? `${lines[lines.length - 1]} ${word}`
            : word;
          if (
            g.measureText(next).width > right - left &&
            lines[lines.length - 1]
          )
            lines.push(word);
          else lines[lines.length - 1] = next;
        }
        lines.forEach((line, i) =>
          g.fillText(
            line,
            left + (right - left) / 2,
            h / 2 + (i - (lines.length - 1) / 2) * 18,
          ),
        );
        g.textAlign = "left";
        return;
      }

      for (const lane of ["you", "agent"]) {
        const points = levels[lane];
        while (points.length && now - points[0].t > WINDOW_MS) points.shift();
        g.fillStyle = color(lane === "you" ? "--fg-1" : "--accent-2");
        for (const p of points) {
          const barH = Math.max(1, p.v * half * 2);
          g.fillRect(x(p.t), lanes[lane] - barH / 2, 2, barH);
        }
      }

      marks = marks.filter((m) => now - (m.t1 ?? m.t) < WINDOW_MS);
      for (const m of marks) {
        if (m.kind === "latency") {
          const x0 = Math.max(left, x(m.t0));
          const x1 = x(m.t1);
          const y = h / 2;
          g.fillStyle = color("--fg-2");
          g.fillRect(x0, y, x1 - x0, 1);
          g.fillRect(x0, y - 5, 1, 10);
          g.fillRect(x1 - 1, y - 5, 1, 10);
          g.textAlign = "center";
          label(`${m.ms} ms`, (x0 + x1) / 2, y - 13, "--accent-2", 600);
          g.textAlign = "left";
        } else {
          const xc = x(m.t);
          g.fillStyle = color("--accent");
          g.fillRect(xc - 1, lanes.agent - half - 8, 2, half * 2 + 16);
          label(T.cut, xc + 6, lanes.agent - half - 2, "--accent", 600);
        }
      }
    }

    function loop() {
      draw();
      frame = requestAnimationFrame(loop);
    }

    window.addEventListener("resize", draw);
    document.fonts?.ready.then(draw);
    draw();
    return {
      level,
      mark,
      run: () => {
        cancelAnimationFrame(frame);
        loop();
      },
      stop: () => {
        cancelAnimationFrame(frame);
        draw();
      },
    };
  })();

  $("voice-toggle").addEventListener("click", () =>
    call ? endCall() : startCall(),
  );
})();
