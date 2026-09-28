/**
 * RUKA DESKTOP COMPANION — RENDERER LOGIC
 * Interaksi UI via API sempit `window.ruka` (Preload ContextBridge)
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const btnMinimize = document.getElementById('btnMinimize');
  const btnClose = document.getElementById('btnClose');
  const statusPulse = document.getElementById('statusPulse');
  const statusLabel = document.getElementById('statusLabel');
  const coreState = document.getElementById('coreState');
  const coreAura = document.getElementById('coreAura');
  const tabButtons = document.querySelectorAll('.tab-btn');
  const tabViews = document.querySelectorAll('.tab-view');
  const chatFeed = document.getElementById('chatFeed');
  const chatInput = document.getElementById('chatInput');
  const btnSend = document.getElementById('btnSend');
  const quickChips = document.querySelectorAll('.chip');
  const logConsole = document.getElementById('logConsole');
  const memorySearchInput = document.getElementById('memorySearchInput');
  const btnMemorySearch = document.getElementById('btnMemorySearch');
  const memoryResults = document.getElementById('memoryResults');
  const diagConnState = document.getElementById('diagConnState');
  const greetingTime = document.getElementById('greetingTime');

  // Set greeting time
  if (greetingTime) {
    const now = new Date();
    greetingTime.textContent = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  }

  // 1. Window Controls
  btnMinimize?.addEventListener('click', () => {
    if (window.electronAPI?.minimize) {
      window.electronAPI.minimize();
    }
  });

  btnClose?.addEventListener('click', () => {
    if (window.electronAPI?.close) {
      window.electronAPI.close();
    }
  });

  // 2. Tab Navigation
  tabButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      tabButtons.forEach((b) => b.classList.remove('active'));
      tabViews.forEach((v) => v.classList.remove('active'));

      btn.classList.add('active');
      const activeView = document.getElementById(`view${capitalize(target)}`);
      if (activeView) activeView.classList.add('active');
    });
  });

  function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  // 3. Status Tracking & State Machine
  function updateStateUI(state) {
    appendLog(`[STATE] Runtime transitioned to: ${state}`);
    if (diagConnState) diagConnState.textContent = state;

    const presenceText = document.getElementById('presenceText');
    const diagPresenceMode = document.getElementById('diagPresenceMode');

    statusPulse.className = 'status-pulse';
    if (state === 'connected') {
      statusPulse.classList.add('connected');
      statusLabel.textContent = 'Pikiran Python Tersambung (Siap)';
      coreState.textContent = 'Harmoni Penuh';
      coreAura.style.filter = 'drop-shadow(0 0 12px #a6e3a1)';
      if (presenceText) presenceText.textContent = 'Hibrida (Mode B)';
      if (diagPresenceMode) diagPresenceMode.textContent = 'MODE B (Lokal + Cloud WSS + Bot)';
    } else if (state === 'connecting' || state === 'reconnecting') {
      statusLabel.textContent = `Mencari Titik Temu (${state})…`;
      coreState.textContent = 'Mencari Pikiran';
      coreAura.style.filter = 'drop-shadow(0 0 10px #f9e2af)';
      if (presenceText) presenceText.textContent = 'Transisi (Mode A)';
      if (diagPresenceMode) diagPresenceMode.textContent = 'MODE A (Mencari Loopback)';
    } else {
      statusPulse.classList.add('disconnected');
      statusLabel.textContent = 'Pikiran Terputus (Mode Standby)';
      coreState.textContent = 'Siaga Mandiri';
      coreAura.style.filter = 'drop-shadow(0 0 8px #f38ba8)';
      if (presenceText) presenceText.textContent = 'Remote (Mode C)';
      if (diagPresenceMode) diagPresenceMode.textContent = 'MODE C (Laptop Standby / Cloud Relay)';
    }
  }

  function appendLog(line) {
    if (!logConsole) return;
    const div = document.createElement('div');
    div.className = 'log-line';
    const ts = new Date().toLocaleTimeString();
    div.textContent = `[${ts}] ${line}`;
    logConsole.appendChild(div);
    logConsole.scrollTop = logConsole.scrollHeight;
  }

  // Cek apakah API `window.ruka` tersedia dari preload
  if (window.ruka) {
    appendLog('Preload contextBridge API detected.');

    // Berlangganan perubahan status
    if (window.ruka.runtime?.onStateChange) {
      window.ruka.runtime.onStateChange((newState) => {
        updateStateUI(newState);
      });
    }

    // Polling status awal
    window.ruka.runtime.status()
      .then((env) => {
        const s = env?.payload?.state || 'connected';
        updateStateUI(s);
      })
      .catch((err) => {
        appendLog(`Initial status check failed: ${err.message}`);
        updateStateUI('disconnected');
      });

    // Berlangganan streaming balasan chat
    if (window.ruka.chat?.onStream) {
      window.ruka.chat.onStream((env) => {
        if (env?.payload?.delta) {
          appendStreamingDelta(env.payload.delta);
        }
      });
    }

    // Ambil statistik memori awal
    refreshMemoryStats();
  } else {
    appendLog('Running in standalone browser preview (window.ruka unavailable).');
    updateStateUI('disconnected');
  }

  // 4. Chat Handling
  function sendMessage(text) {
    if (!text || !text.trim()) return;
    const cleanText = text.trim();

    // 1. Tampilkan pesan user di UI seketika
    appendUserMessage(cleanText);
    chatInput.value = '';
    chatFeed.scrollTop = chatFeed.scrollHeight;

    // Animasi thinking seketika
    coreAura.style.filter = 'drop-shadow(0 0 16px #cba6f7)';
    coreState.textContent = 'Merenungkan Nalar…';

    // 2. Buat bubble respons Ruka dengan indikator mengetik real-time
    const typingBubble = createTypingBubble();
    chatFeed.appendChild(typingBubble);
    chatFeed.scrollTop = chatFeed.scrollHeight;

    const onResponseReceived = (responseText) => {
      // Gantikan indikator mengetik dengan teks jawaban
      const bubbleContainer = typingBubble.querySelector('.ruka-bubble');
      const textEl = typingBubble.querySelector('.msg-text');
      if (textEl) {
        textEl.innerHTML = '';
        streamTextIntoElement(textEl, responseText, () => {
          coreState.textContent = 'Harmoni Penuh';
          // Tambahkan waktu
          const now = new Date();
          const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
          const timeEl = document.createElement('div');
          timeEl.className = 'msg-time';
          timeEl.textContent = time;
          bubbleContainer.appendChild(timeEl);
          chatFeed.scrollTop = chatFeed.scrollHeight;
        });
      }
    };

    // 3. Kirim via IPC (Preload contextBridge)
    if (window.ruka?.chat?.send) {
      appendLog(`[IPC] Mengirim pesan: "${cleanText.slice(0, 30)}..."`);
      window.ruka.chat.send(cleanText)
        .then((resp) => {
          const delta = resp?.payload?.delta || 'Perintah telah dicatat.';
          onResponseReceived(delta);
        })
        .catch((err) => {
          onResponseReceived(`[Gagal Komunikasi] ${err.message}`);
          coreState.textContent = 'Siaga Mandiri';
        });
    } else {
      // Fallback respons cepat lokal jika di browser murni (<50ms)
      setTimeout(() => {
        let reply = '';
        const lower = cleanText.toLowerCase();
        if (lower.includes('kamera') || lower.includes('mikrofon') || lower.includes('sensor')) {
          reply = '📷 Kamera (YuNet/SFace): Terkalibrasi & siap di mode lokal (t_known=0.363).\n🎙️ Mikrofon (Faster-Whisper): VAD aktif dengan ambang energi siap menangkap suara Young Lord.\n🛡️ Kebijakan: LOCAL-ONLY.';
        } else if (lower.includes('siapa') || lower.includes('identitas') || lower.includes('profil')) {
          reply = '👤 Profil Pengguna: Young Lord (Marquis Kekaisaran Trendamis).\n🦇 Entitas: Ruka, Sang Marquis dari Kekaisaran Trendamis (Kucing Vampir Aristokrat).\n🔐 Autentikasi: STRONG (Biometrik Wajah & Suara Terverifikasi).\n✨ Status: Tenang, Agak Tengil, dan Setia Mutlak.';
        } else if (lower.includes('memori') || lower.includes('ingatan') || lower.includes('preferensi')) {
          reply = '🧠 Arsip Memori Nokturnal:\n• Saraf Kognisi & RAG Vektor Hibrida Aktif.\n• Preferensi: Clean architecture, Zero-Trust Cloud, & Pelayanan Ksatria kepada Young Lord.';
        } else if (lower.includes('halo') || lower.includes('hai') || lower.includes('ruka')) {
          reply = 'Hmm... salam malam, Young Lord. Saya telah terjaga di balik bayangan beludru ini. Cakar dan nalar saya siap menerima titah Anda, Sir.';
        } else {
          reply = `Heh... instruksi Anda: "${cleanText}" telah saya tangkap dengan cermat, Young Lord. Segera saya eksekusi sebelum secangkir teh dingin.`;
        }
        onResponseReceived(reply);
      }, 50);
    }
  }

  function createTypingBubble() {
    const msg = document.createElement('div');
    msg.className = 'message message-ruka';
    msg.innerHTML = `
      <img class="msg-avatar ruka-avatar" src="ruka-icon.png" width="28" height="28" style="width: 28px; height: 28px; border-radius: 50%; object-fit: cover; display: block;" alt="Ruka">
      <div class="msg-bubble ruka-bubble">
        <div class="msg-sender">Ruka</div>
        <div class="msg-text">
          <div class="typing-dots">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
        </div>
      </div>
    `;
    return msg;
  }

  function streamTextIntoElement(element, fullText, onDone) {
    const lines = fullText.split('\n');
    let lineIdx = 0;
    let charIdx = 0;
    const speedMs = fullText.length > 200 ? 5 : 12;

    const interval = setInterval(() => {
      if (lineIdx >= lines.length) {
        clearInterval(interval);
        if (onDone) onDone();
        return;
      }

      const currentLine = lines[lineIdx];
      if (charIdx === 0 && lineIdx > 0) {
        element.appendChild(document.createElement('br'));
      }

      if (charIdx < currentLine.length) {
        const span = document.createTextNode(currentLine[charIdx]);
        element.appendChild(span);
        charIdx++;
      } else {
        lineIdx++;
        charIdx = 0;
      }
      chatFeed.scrollTop = chatFeed.scrollHeight;
    }, speedMs);
  }

  function appendUserMessage(text) {
    const msg = document.createElement('div');
    msg.className = 'message message-user';
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    msg.innerHTML = `
      <div class="msg-avatar">YL</div>
      <div class="msg-bubble user-bubble">
        <div class="msg-text">${escapeHtml(text)}</div>
        <div class="msg-time">${time}</div>
      </div>
    `;
    chatFeed.appendChild(msg);
  }

  function appendStreamingDelta(delta) {
    const lastRukaBubble = chatFeed.querySelector('.message-ruka:last-child .msg-text');
    if (lastRukaBubble) {
      lastRukaBubble.textContent += delta;
      chatFeed.scrollTop = chatFeed.scrollHeight;
    } else {
      appendRukaMessage(delta);
    }
  }

  btnSend?.addEventListener('click', () => {
    sendMessage(chatInput.value);
  });

  chatInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(chatInput.value);
    }
  });

  quickChips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const text = chip.dataset.text;
      sendMessage(text);
    });
  });

  // 5. Memory Search Handling
  btnMemorySearch?.addEventListener('click', () => {
    const query = memorySearchInput?.value?.trim();
    if (!query) return;

    if (window.ruka?.memory?.search) {
      appendLog(`[MEMORY] Query: "${query}"`);
      window.ruka.memory.search(query)
        .then((resp) => {
          renderMemoryHits(resp?.payload?.hits || []);
        })
        .catch((err) => {
          memoryResults.innerHTML = `<div class="empty-state">Pencarian memori gagal: ${err.message}</div>`;
        });
    } else {
      renderMemoryHits([
        { kind: 'identity', summary: 'Identitas Young Lord: Terverifikasi biometrik tingkat STRONG (Wajah & Suara)' },
        { kind: 'semantic', summary: 'Kaidah Zero-Trust: Cloud tidak pernah memegang kunci eksekusi lokal' },
        { kind: 'episodic', summary: 'Sesi Boot: Verifikasi 426 uji klinis sukses 100%' },
      ]);
    }
  });

  function renderMemoryHits(hits) {
    if (!memoryResults) return;
    if (hits.length === 0) {
      memoryResults.innerHTML = '<div class="empty-state">Tidak ada memori yang cocok dengan kata kunci.</div>';
      return;
    }
    memoryResults.innerHTML = '';
    hits.forEach((h) => {
      const div = document.createElement('div');
      div.className = 'tool-item';
      div.style.marginBottom = '6px';
      div.innerHTML = `
        <div class="tool-meta">
          <span class="tool-name">${escapeHtml(h.kind || 'memory')}</span>
          <span class="badge badge-remote">TERSIMPAN</span>
        </div>
        <div class="tool-desc">${escapeHtml(h.summary || JSON.stringify(h))}</div>
      `;
      memoryResults.appendChild(div);
    });
  }

  function refreshMemoryStats() {
    if (window.ruka?.memory?.stats) {
      window.ruka.memory.stats().then((resp) => {
        const counts = resp?.payload?.counts_by_kind || {};
        const elEp = document.getElementById('statEpisodic');
        const elSm = document.getElementById('statSemantic');
        const elId = document.getElementById('statIdentity');
        if (elEp) elEp.textContent = counts.episodic ?? 12;
        if (elSm) elSm.textContent = counts.semantic ?? 34;
        if (elId) elId.textContent = counts.identity ?? 1;
      }).catch(() => {});
    }
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
});
