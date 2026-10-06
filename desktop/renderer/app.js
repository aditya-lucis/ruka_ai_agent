/**
 * RUKA DESKTOP COMPANION — RENDERER LOGIC
 * Interaksi UI via API sempit `window.ruka` (Preload ContextBridge)
 * Fitur: Saling Ngobrol dengan Suara (STT/TTS), Akses Kamera HUD Lokal, & Multimodal Scan Gambar/Berkas
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements: Window & Navigation
  const btnMinimize = document.getElementById('btnMinimize');
  const btnMaximize = document.getElementById('btnMaximize');
  const btnClose = document.getElementById('btnClose');
  const iconMaximize = btnMaximize?.querySelector('.icon-maximize');
  const iconRestore = btnMaximize?.querySelector('.icon-restore');
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

  // Elements: Voice (TTS & STT)
  const btnToggleVoice = document.getElementById('btnToggleVoice');
  const btnMic = document.getElementById('btnMic');

  // Elements: Attachment & Scan
  const btnAttachFile = document.getElementById('btnAttachFile');
  const fileInput = document.getElementById('fileInput');
  const attachmentBar = document.getElementById('attachmentBar');
  const attachmentThumbnailWrapper = document.getElementById('attachmentThumbnailWrapper');
  const attachmentThumbnail = document.getElementById('attachmentThumbnail');
  const attachmentFileIcon = document.getElementById('attachmentFileIcon');
  const attachmentName = document.getElementById('attachmentName');
  const attachmentMeta = document.getElementById('attachmentMeta');
  const btnRemoveAttachment = document.getElementById('btnRemoveAttachment');

  // Elements: Camera Viewfinder HUD
  const btnOpenCamera = document.getElementById('btnOpenCamera');
  const cameraModal = document.getElementById('cameraModal');
  const cameraBackdrop = document.getElementById('cameraBackdrop');
  const btnCloseCamera = document.getElementById('btnCloseCamera');
  const cameraVideo = document.getElementById('cameraVideo');
  const cameraCanvas = document.getElementById('cameraCanvas');
  const btnSnapPhoto = document.getElementById('btnSnapPhoto');

  // State Management
  let voiceEnabled = true;
  let isRecording = false;
  let speechRecognition = null;
  let cameraStream = null;
  let currentAttachment = null; // { type, isImage, name, mime_type, data, text_content }
  let availableVoices = [];

  // Set greeting time
  if (greetingTime) {
    const now = new Date();
    greetingTime.textContent = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  }

  // Bind initial speech synthesis voices
  if ('speechSynthesis' in window) {
    const populateVoices = () => {
      availableVoices = window.speechSynthesis.getVoices();
    };
    populateVoices();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = populateVoices;
    }
  }

  // 1. Window Controls (Minimize, Maximize/Restore, Close to tray)
  function updateMaximizeUI(isMax) {
    if (isMax) {
      iconMaximize?.classList.add('hidden');
      iconRestore?.classList.remove('hidden');
      if (btnMaximize) btnMaximize.title = 'Pulihkan Ukuran Jendela';
    } else {
      iconMaximize?.classList.remove('hidden');
      iconRestore?.classList.add('hidden');
      if (btnMaximize) btnMaximize.title = 'Maksimalkan Jendela';
    }
  }

  btnMinimize?.addEventListener('click', () => {
    if (window.electronAPI?.minimize) {
      window.electronAPI.minimize();
    }
  });

  btnMaximize?.addEventListener('click', async () => {
    if (window.electronAPI?.maximize) {
      const isMax = await window.electronAPI.maximize();
      updateMaximizeUI(isMax);
    }
  });

  btnClose?.addEventListener('click', () => {
    if (window.electronAPI?.close) {
      window.electronAPI.close();
    }
  });

  // Cek status maximized awal
  if (window.electronAPI?.isMaximized) {
    window.electronAPI.isMaximized().then(updateMaximizeUI).catch(() => { });
  }

  // Pantau perubahan status maximize dari event jendela Electron
  if (window.electronAPI?.onMaximizeChange) {
    window.electronAPI.onMaximizeChange((isMax) => {
      updateMaximizeUI(isMax);
    });
  }

  // Klik ganda titlebar untuk toggle maximize (standar desktop UX)
  const titlebar = document.querySelector('.titlebar');
  titlebar?.addEventListener('dblclick', async (e) => {
    if (e.target.closest('button') || e.target.closest('.brand-avatar-mini')) return;
    if (window.electronAPI?.maximize) {
      const isMax = await window.electronAPI.maximize();
      updateMaximizeUI(isMax);
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

  // Preload IPC initialization
  if (window.ruka) {
    appendLog('Preload contextBridge API detected.');

    if (window.ruka.runtime?.onStateChange) {
      window.ruka.runtime.onStateChange((newState) => {
        updateStateUI(newState);
      });
    }

    window.ruka.runtime.status()
      .then((env) => {
        const s = env?.payload?.state || 'connected';
        updateStateUI(s);
      })
      .catch((err) => {
        appendLog(`Initial status check failed: ${err.message}`);
        updateStateUI('disconnected');
      });

    if (window.ruka.chat?.onStream) {
      window.ruka.chat.onStream((env) => {
        if (env?.payload?.delta) {
          appendStreamingDelta(env.payload.delta);
        }
      });
    }

    if (window.ruka.kernel?.onEvent) {
      window.ruka.kernel.onEvent((event) => {
        if (!event || !event.topic) return;

        // 1. Lunar Clock & Diurnal Moon Phase
        if (event.topic.startsWith('lunar.')) {
          const payload = event.payload || {};
          const lunarBadge = document.getElementById('lunarBadge');
          const lunarText = document.getElementById('lunarText');
          const lunarIcon = document.getElementById('lunarIcon');
          if (lunarText && payload.phase) {
            const icons = {
              new_moon: '🌑',
              waxing_crescent: '🌒',
              first_quarter: '🌓',
              waxing_gibbous: '🌔',
              full_moon: '🌕',
              waning_gibbous: '🌖',
              last_quarter: '🌗',
              waning_crescent: '🌘',
            };
            const names = {
              new_moon: 'Bulan Baru (Hening)',
              waxing_crescent: 'Sabit Awal',
              first_quarter: 'Kuartal Pertama',
              waxing_gibbous: 'Bulan Cembung',
              full_moon: 'Purnama (Puncak)',
              waning_gibbous: 'Cembung Akhir',
              last_quarter: 'Kuartal Terakhir',
              waning_crescent: 'Sabit Akhir',
            };
            if (lunarIcon) lunarIcon.textContent = icons[payload.phase] || '🌙';
            lunarText.textContent = names[payload.phase] || payload.phase;
            if (lunarBadge) lunarBadge.title = `Fase: ${names[payload.phase] || payload.phase} | Jam: ${payload.hour ?? ''} ${payload.isQuietHours ? '(Jam Malam)' : ''}`;
          }
        }

        // 2. Avatar Viseme & Pose Animation
        if (event.topic === 'avatar.viseme' || event.topic === 'avatar.pose') {
          const coreAura = document.getElementById('coreAura');
          if (coreAura) {
            coreAura.classList.add('viseme-pulse');
            setTimeout(() => coreAura.classList.remove('viseme-pulse'), 150);
          }
        }

        // 3. Notification Dosing
        if (event.topic === 'notification.dosed') {
          const payload = event.payload || {};
          appendLog(`[NOTIF DOSING] ${payload.title || 'Pemberitahuan'}: ${payload.body || ''}`);
        }

        // 4. Kernel Lifecycle
        if (event.topic === 'noctis.boot' || event.topic === 'noctis.ready') {
          appendLog(`[KERNEL] EventBus V3: ${event.topic} (Producer: ${event.producer})`);
        }

        // 5. Organ Telemetry Real-Time Pulse
        const organPrefix = event.topic.split('.')[0];
        const organCardMap = {
          heart: 'organCardHeart',
          palace: 'organCardPalace',
          converse: 'organCardConverse',
          eyes: 'organCardEyes',
          ear: 'organCardEar',
          avatar: 'organCardAvatar',
          hands: 'organCardHands',
          brain: 'organCardBrain',
          forge: 'organCardForge',
          noctis: 'organCardKernel',
          os: 'organCardKernel',
        };
        const cardId = organCardMap[organPrefix];
        if (cardId) {
          const card = document.getElementById(cardId);
          if (card) {
            card.classList.add('viseme-pulse');
            setTimeout(() => card.classList.remove('viseme-pulse'), 250);
          }
        }
      });
    }

    refreshMemoryStats();
  } else {
    appendLog('Running in standalone browser preview (window.ruka unavailable).');
    updateStateUI('disconnected');
  }

  // ==========================================================================
  // FITUR 1: SUARA 100% MANUSIA (NEURAL SPEECH SYNTHESIS & SPEECH-TO-TEXT)
  // ==========================================================================
  let currentAudioElement = null;

  // Hentikan semua audio yang sedang diputar (baik neural maupun fallback)
  function stopAllSpeech() {
    if (currentAudioElement) {
      try {
        currentAudioElement.pause();
        currentAudioElement.currentTime = 0;
      } catch (_) { }
      currentAudioElement = null;
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    document.querySelectorAll('.msg-speak-btn.speaking').forEach((btn) => {
      btn.classList.remove('speaking');
    });
  }

  // Toggle Voice Output (Mulut Ruka)
  btnToggleVoice?.addEventListener('click', () => {
    voiceEnabled = !voiceEnabled;
    if (voiceEnabled) {
      btnToggleVoice.classList.remove('muted');
      btnToggleVoice.classList.add('active');
      btnToggleVoice.title = 'Suara Ruka: Aktif (Klik untuk membisukan)';
      btnToggleVoice.querySelector('.voice-status-text').textContent = 'Suara Ruka';
      appendLog('[VOICE] Suara Ruka 100% Manusia (Neural) diaktifkan.');
    } else {
      btnToggleVoice.classList.remove('active');
      btnToggleVoice.classList.add('muted');
      btnToggleVoice.title = 'Suara Ruka: Bisu (Klik untuk aktifkan)';
      btnToggleVoice.querySelector('.voice-status-text').textContent = 'Bisu';
      stopAllSpeech();
      appendLog('[VOICE] Suara Ruka dibisukan.');
    }
  });

  // Pembersih teks untuk suara: Hapus seluruh peragaan aksi, tanda kurung, bintang, dan emoji
  function cleanTextForSpeech(raw) {
    return raw
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // Pertahankan teks judul tautan markdown, buang URL-nya
      .replace(/\([^)]*\)/g, ' ')      // Hapus (tersenyum tipis...), (Aku menyeringai...)
      .replace(/\[[^\]]*\]/g, ' ')     // Hapus [Sensor...]
      .replace(/\*[^*]+\*/g, ' ')      // HAPUS seluruh peragaan peran dalam bintang (*tersenyum tipis*, *menatap santai*)
      .replace(/_[^_]+_/g, ' ')        // HAPUS peragaan dalam underscore
      .replace(/```[\s\S]*?```/g, ' ') // Hilangkan blok kode
      .replace(/`([^`]+)`/g, '$1')     // Hilangkan inline code
      .replace(/https?:\/\/\S+/g, ' ') // Hilangkan tautan url
      .replace(/([\u2700-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|[\u2011-\u26FF]|\uD83E[\uDD10-\uDDFF])/g, '') // Hapus emoji
      .replace(/[•#~^—]/g, ' ')        // Hapus dekorasi karakter
      .replace(/\s+/g, ' ')
      .trim();
  }

  // Fallback Suara Browser (jika backend offline)
  function fallbackSpeechSynthesis(spokenText, speakBtn) {
    if (!('speechSynthesis' in window)) {
      if (speakBtn) speakBtn.classList.remove('speaking');
      return;
    }
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(spokenText);
    if (availableVoices.length === 0) {
      availableVoices = window.speechSynthesis.getVoices();
    }
    const idVoice = availableVoices.find(v => v.lang.startsWith('id') || v.lang.startsWith('ms'));
    const gbVoice = availableVoices.find(v => v.lang.includes('en-GB') || v.name.includes('David') || v.name.includes('George'));

    if (idVoice) {
      utterance.voice = idVoice;
    } else if (gbVoice) {
      utterance.voice = gbVoice;
    }

    utterance.pitch = 0.88;
    utterance.rate = 0.95;

    utterance.onend = () => {
      if (speakBtn) speakBtn.classList.remove('speaking');
    };
    utterance.onerror = () => {
      if (speakBtn) speakBtn.classList.remove('speaking');
    };

    window.speechSynthesis.speak(utterance);
  }

  // Fungsi Berbicara Ruka (Text-to-Speech) - 100% Manusia Neural Studio
  function speakRukaResponse(text, speakBtn) {
    stopAllSpeech();

    const spokenText = cleanTextForSpeech(text);
    if (!spokenText) return;

    if (speakBtn) {
      speakBtn.classList.add('speaking');
    }

    // Prioritaskan Saraf Neural TTS 100% Manusia (Edge Neural Studio)
    if (window.ruka?.voice?.synthesize) {
      appendLog('[VOICE] Meracik vokal saraf 100% manusia (Ardi Neural + Prosodi F0)...');
      window.ruka.voice.synthesize({ text: spokenText })
        .then((res) => {
          const audioUrl = res?.payload?.audioUrl;
          if (audioUrl) {
            const audio = new Audio();
            currentAudioElement = audio;

            let playUrl = audioUrl;
            if (audioUrl.startsWith('data:')) {
              try {
                const parts = audioUrl.split(',');
                const mime = parts[0].match(/:(.*?);/)?.[1] || 'audio/mpeg';
                const bin = atob(parts[1]);
                const u8 = new Uint8Array(bin.length);
                for (let i = 0; i < bin.length; i++) {
                  u8[i] = bin.charCodeAt(i);
                }
                const blob = new Blob([u8], { type: mime });
                playUrl = URL.createObjectURL(blob);
              } catch (convErr) {
                console.warn('[VOICE] Blob conversion warning:', convErr);
              }
            }

            audio.onended = () => {
              if (speakBtn) speakBtn.classList.remove('speaking');
              if (currentAudioElement === audio) currentAudioElement = null;
              if (playUrl.startsWith('blob:')) URL.revokeObjectURL(playUrl);
            };

            audio.onerror = (err) => {
              console.warn('[VOICE] Audio playback error:', err);
              if (speakBtn) speakBtn.classList.remove('speaking');
              if (currentAudioElement === audio) currentAudioElement = null;
              if (playUrl.startsWith('blob:')) URL.revokeObjectURL(playUrl);
              appendLog('[VOICE] Gagal memutar audio neural, beralih ke suara lokal.');
              fallbackSpeechSynthesis(spokenText, speakBtn);
            };

            audio.src = playUrl;
            audio.play().catch((playErr) => {
              console.warn('[VOICE] Play err:', playErr);
              fallbackSpeechSynthesis(spokenText, speakBtn);
            });
            return;
          }
          console.warn('[VOICE] Tiada audio URL dari backend, beralih ke fallback browser.');
          fallbackSpeechSynthesis(spokenText, speakBtn);
        })
        .catch((err) => {
          console.warn('[VOICE] Synthesize IPC error:', err);
          fallbackSpeechSynthesis(spokenText, speakBtn);
        });
    } else {
      fallbackSpeechSynthesis(spokenText, speakBtn);
    }
  }

  // Format awal dan pasang listener pada bubble pembuka
  const initialBubble = chatFeed.querySelector('.message-ruka');
  if (initialBubble) {
    const textEl = initialBubble.querySelector('.msg-text');
    const speakBtn = initialBubble.querySelector('.msg-speak-btn');
    const copyBtn = initialBubble.querySelector('.msg-copy-btn');
    if (textEl) {
      const rawGreeting = textEl.textContent.trim();
      textEl.innerHTML = formatMarkdown(rawGreeting);
      if (copyBtn) copyBtn.setAttribute('data-raw-text', rawGreeting);
      if (speakBtn) {
        speakBtn.addEventListener('click', () => {
          speakRukaResponse(rawGreeting, speakBtn);
        });
      }
    }
  }

  // ==========================================================================
  // FITUR 1B: MIKROFON (SPEECH-TO-TEXT VIA WEB AUDIO WAV ENCODER + PYTHON ASR)
  // ==========================================================================
  let audioStream = null;
  let audioContext = null;
  let scriptProcessor = null;
  let recordedAudioSamples = [];
  let recordTimerInterval = null;
  let recordSeconds = 0;

  function encodeWAV(samples, sampleRate = 16000) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    function writeString(offset, string) {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    }

    writeString(0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM format
    view.setUint16(22, 1, true); // Mono channel
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true); // byte rate (sampleRate * 1 channel * 2 bytes)
    view.setUint16(32, 2, true); // block align
    view.setUint16(34, 16, true); // 16-bit
    writeString(36, 'data');
    view.setUint32(40, samples.length * 2, true);

    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }

    return new Blob([view], { type: 'audio/wav' });
  }

  async function startRecording() {
    try {
      appendLog('[VOICE] Membuka mikrofon via Web Audio API...');
      audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      const source = audioContext.createMediaStreamSource(audioStream);
      scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);

      recordedAudioSamples = [];
      isRecording = true;
      recordSeconds = 0;

      scriptProcessor.onaudioprocess = (e) => {
        if (!isRecording) return;
        const input = e.inputBuffer.getChannelData(0);
        for (let i = 0; i < input.length; i++) {
          recordedAudioSamples.push(input[i]);
        }
      };

      source.connect(scriptProcessor);
      scriptProcessor.connect(audioContext.destination);

      btnMic.classList.add('recording');
      btnMic.title = 'Sedang merekam... (Klik lagi untuk selesai & kirim)';
      chatInput.placeholder = '🔴 Merekam suara Anda (00:00)... Klik tombol mikrofon lagi setelah selesai';
      coreState.textContent = 'Mendengarkan Suara';
      coreAura.style.filter = 'drop-shadow(0 0 16px #f38ba8)';

      recordTimerInterval = setInterval(() => {
        recordSeconds++;
        const m = String(Math.floor(recordSeconds / 60)).padStart(2, '0');
        const s = String(recordSeconds % 60).padStart(2, '0');
        chatInput.placeholder = `🔴 Merekam suara Anda (${m}:${s})... Klik mikrofon lagi untuk selesai`;
      }, 1000);

      appendLog('[VOICE] Mikrofon aktif merekam (16kHz Mono PCM).');
    } catch (err) {
      appendLog(`[VOICE-ERROR] Gagal membuka mikrofon: ${err.message}`);
      alert(`Tidak dapat mengakses mikrofon: ${err.message}\nPastikan izin mikrofon diberikan di Windows.`);
      stopRecording(false);
    }
  }

  async function stopRecording(shouldTranscribe = true) {
    if (!isRecording) return;
    isRecording = false;

    if (recordTimerInterval) {
      clearInterval(recordTimerInterval);
      recordTimerInterval = null;
    }

    if (scriptProcessor) {
      scriptProcessor.disconnect();
      scriptProcessor = null;
    }
    if (audioStream) {
      audioStream.getTracks().forEach((track) => track.stop());
      audioStream = null;
    }
    if (audioContext && audioContext.state !== 'closed') {
      audioContext.close().catch(() => { });
      audioContext = null;
    }

    btnMic.classList.remove('recording');
    btnMic.setAttribute('title', 'Bicara dengan Suara (Mikrofon)');
    coreState.textContent = 'Harmoni Penuh';
    coreAura.style.filter = 'drop-shadow(0 0 12px #a6e3a1)';

    if (!shouldTranscribe || recordedAudioSamples.length < 4000) {
      chatInput.placeholder = 'Tulis instruksi atau bicara dengan Ruka... (Enter kirim)';
      return;
    }

    chatInput.placeholder = '⏳ Menerjemahkan suara Young Lord ke teks…';
    appendLog(`[VOICE] Mengodekan ${recordedAudioSamples.length} sampel PCM ke WAV...`);

    const wavBlob = encodeWAV(recordedAudioSamples, 16000);
    const reader = new FileReader();
    reader.onload = async (ev) => {
      const dataUrl = ev.target.result;
      const base64Wav = dataUrl.split(',')[1];

      if (window.ruka?.voice?.transcribe) {
        try {
          appendLog('[VOICE] Mengirim WAV ke Python ASR...');
          const resp = await window.ruka.voice.transcribe(base64Wav);
          const recognizedText = resp?.payload?.text || '';
          const errMsg = resp?.payload?.error;

          if (recognizedText && recognizedText.trim()) {
            appendLog(`[VOICE] Transkripsi sukses: "${recognizedText}"`);
            chatInput.value = recognizedText;
            chatInput.placeholder = 'Tulis instruksi atau bicara dengan Ruka... (Enter kirim)';
            // Otomatis kirim pesan suara ke Ruka!
            sendMessage(recognizedText);
          } else {
            appendLog(`[VOICE] Tidak ada kata terdeteksi: ${errMsg || 'suara terlalu pelan'}`);
            chatInput.placeholder = errMsg || 'Suara tidak terdengar jelas. Coba bicara lebih dekat ke mikrofon.';
          }
        } catch (ipcErr) {
          appendLog(`[VOICE-ERROR] Transcribe IPC gagal: ${ipcErr.message}`);
          chatInput.placeholder = 'Gagal transkripsi suara.';
        }
      } else {
        appendLog('[VOICE] window.ruka.voice.transcribe tidak tersedia.');
        chatInput.placeholder = 'ASR loopback belum tersambung.';
      }
    };
    reader.readAsDataURL(wavBlob);
  }

  btnMic?.addEventListener('click', () => {
    if (!isRecording) {
      startRecording();
    } else {
      stopRecording(true);
    }
  });

  // ==========================================================================
  // FITUR 2: AKSES KAMERA (SENSOR OPTIK YUNET & SFACE HUD)
  // ==========================================================================

  btnOpenCamera?.addEventListener('click', async () => {
    try {
      cameraModal.classList.remove('hidden');
      appendLog('[CAMERA] Menginisialisasi sensor optik kamera...');
      cameraStream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
        audio: false,
      });
      cameraVideo.srcObject = cameraStream;
      await cameraVideo.play();
      coreState.textContent = 'Mata Sensor Aktif';
      coreAura.style.filter = 'drop-shadow(0 0 16px #89b4fa)';
      appendLog('[CAMERA] Sensor visual YuNet aktif & menayangkan feed.');
    } catch (err) {
      appendLog(`[CAMERA-ERROR] Akses kamera gagal: ${err.message}`);
      alert(`Tidak dapat mengakses kamera: ${err.message}\nPastikan izin kamera diberikan di Windows.`);
      closeCameraModal();
    }
  });

  function closeCameraModal() {
    if (cameraStream) {
      cameraStream.getTracks().forEach((track) => track.stop());
      cameraStream = null;
    }
    cameraVideo.srcObject = null;
    cameraModal.classList.add('hidden');
    coreState.textContent = 'Harmoni Penuh';
    coreAura.style.filter = 'drop-shadow(0 0 12px #a6e3a1)';
    appendLog('[CAMERA] Sensor optik ditutup.');
  }

  btnCloseCamera?.addEventListener('click', closeCameraModal);
  cameraBackdrop?.addEventListener('click', closeCameraModal);

  // Ambil Foto dari Kamera dan Masukkan ke Attachment
  btnSnapPhoto?.addEventListener('click', () => {
    if (!cameraVideo.videoWidth) return;

    cameraCanvas.width = cameraVideo.videoWidth;
    cameraCanvas.height = cameraVideo.videoHeight;
    const ctx = cameraCanvas.getContext('2d');
    ctx.drawImage(cameraVideo, 0, 0, cameraCanvas.width, cameraCanvas.height);

    const dataUrl = cameraCanvas.toDataURL('image/jpeg', 0.88);
    const filename = `snapshot_optik_${new Date().toISOString().slice(11, 19).replace(/:/g, '')}.jpg`;

    setAttachment({
      type: 'image',
      isImage: true,
      name: filename,
      mime_type: 'image/jpeg',
      data: dataUrl,
      sizeStr: `${Math.round(dataUrl.length * 0.75 / 1024)} KB`,
    });

    closeCameraModal();
    chatInput.placeholder = 'Tanyakan sesuatu atau titahkan Ruka untuk meneliti foto ini...';
    chatInput.focus();
    appendLog(`[CAMERA] Tangkapan citra "${filename}" siap dikirim ke nalar Ruka.`);
  });

  // ==========================================================================
  // FITUR 3: SCAN GAMBAR & BERKAS (MULTIMODAL ATTACHMENTS)
  // ==========================================================================

  btnAttachFile?.addEventListener('click', () => {
    fileInput?.click();
  });

  fileInput?.addEventListener('change', (e) => {
    const file = e.target.files?.[0];
    if (file) {
      processSelectedFile(file);
    }
  });

  // Drag and drop gambar/file ke composer atau chat view
  const dragTarget = document.querySelector('.chat-composer');
  dragTarget?.addEventListener('dragover', (e) => {
    e.preventDefault();
    dragTarget.style.borderColor = 'var(--accent-purple)';
    dragTarget.style.boxShadow = '0 0 16px var(--accent-glow)';
  });

  dragTarget?.addEventListener('dragleave', () => {
    dragTarget.style.borderColor = 'var(--border-color)';
    dragTarget.style.boxShadow = 'none';
  });

  dragTarget?.addEventListener('drop', (e) => {
    e.preventDefault();
    dragTarget.style.borderColor = 'var(--border-color)';
    dragTarget.style.boxShadow = 'none';
    const file = e.dataTransfer?.files?.[0];
    if (file) {
      processSelectedFile(file);
    }
  });

  function processSelectedFile(file) {
    const isImg = file.type.startsWith('image/');
    const sizeKB = Math.round(file.size / 1024);
    const sizeStr = sizeKB > 1024 ? `${(sizeKB / 1024).toFixed(1)} MB` : `${sizeKB} KB`;

    const reader = new FileReader();

    if (isImg) {
      reader.onload = (ev) => {
        const dataUrl = ev.target.result;
        setAttachment({
          type: 'image',
          isImage: true,
          name: file.name,
          mime_type: file.type || 'image/jpeg',
          data: dataUrl,
          sizeStr: sizeStr,
        });
        appendLog(`[ATTACH] Gambar "${file.name}" (${sizeStr}) terpasang.`);
      };
      reader.readAsDataURL(file);
    } else {
      // Kode atau berkas teks/dokumen
      reader.onload = (ev) => {
        const textContent = ev.target.result;
        setAttachment({
          type: 'file',
          isImage: false,
          name: file.name,
          mime_type: file.type || 'text/plain',
          text_content: textContent,
          sizeStr: sizeStr,
        });
        appendLog(`[ATTACH] Dokumen/kode "${file.name}" (${sizeStr}) terpasang.`);
      };
      reader.readAsText(file);
    }
  }

  function setAttachment(att) {
    currentAttachment = att;
    attachmentName.textContent = att.name;
    attachmentMeta.textContent = `${att.sizeStr} · Siap di-scan nalar Ruka`;

    if (att.isImage) {
      attachmentThumbnail.src = att.data;
      attachmentThumbnail.classList.remove('hidden');
      attachmentFileIcon.classList.add('hidden');
    } else {
      attachmentThumbnail.classList.add('hidden');
      attachmentFileIcon.classList.remove('hidden');
    }

    attachmentBar.classList.remove('hidden');
  }

  btnRemoveAttachment?.addEventListener('click', () => {
    currentAttachment = null;
    attachmentBar.classList.add('hidden');
    if (fileInput) fileInput.value = '';
    appendLog('[ATTACH] Lampiran dibatalkan.');
  });

  // ==========================================================================
  // FITUR 4: CHAT HANDLING (PENGIRIMAN DENGAN MULTIMODAL & BALASAN SUARA)
  // ==========================================================================

  function sendMessage(text) {
    const cleanText = (text || '').trim();
    if (!cleanText && !currentAttachment) return;

    const attachmentToSend = currentAttachment;

    // 1. Tampilkan pesan user di UI seketika
    appendUserMessage(cleanText, attachmentToSend);
    chatInput.value = '';

    // Bersihkan attachment bar
    currentAttachment = null;
    attachmentBar.classList.add('hidden');
    if (fileInput) fileInput.value = '';
    chatFeed.scrollTop = chatFeed.scrollHeight;

    // Animasi thinking seketika
    coreAura.style.filter = 'drop-shadow(0 0 16px #cba6f7)';
    coreState.textContent = 'Merenungkan Nalar…';

    // 2. Buat bubble respons Ruka dengan indikator mengetik real-time
    const typingBubble = createTypingBubble();
    chatFeed.appendChild(typingBubble);
    chatFeed.scrollTop = chatFeed.scrollHeight;

    const onResponseReceived = (responseText) => {
      // Gantikan indikator mengetik dengan respons terformat AI Bot
      const textEl = typingBubble.querySelector('.msg-text');
      const speakBtn = typingBubble.querySelector('.msg-speak-btn');
      const copyBtn = typingBubble.querySelector('.msg-copy-btn');

      if (textEl) {
        textEl.innerHTML = formatMarkdown(responseText);
        coreState.textContent = 'Harmoni Penuh';
        coreAura.style.filter = 'drop-shadow(0 0 12px #a6e3a1)';
        chatFeed.scrollTop = chatFeed.scrollHeight;

        if (copyBtn) {
          copyBtn.setAttribute('data-raw-text', responseText);
        }

        // Pasang click listener pada tombol speak
        if (speakBtn) {
          speakBtn.onclick = () => {
            speakRukaResponse(responseText, speakBtn);
          };
        }

        // Otomatis bersuara jika mode suara aktif
        if (voiceEnabled) {
          speakRukaResponse(responseText, speakBtn);
        }
      }
    };

    // 3. Kirim via IPC (Preload contextBridge)
    if (window.ruka?.chat?.send) {
      appendLog(`[IPC] Mengirim pesan: "${cleanText.slice(0, 30)}..." (Attachment: ${attachmentToSend ? attachmentToSend.name : 'none'})`);
      window.ruka.chat.send(cleanText, attachmentToSend)
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
        if (attachmentToSend?.isImage) {
          reply = `Hmm... saya telah menatap citra "${attachmentToSend.name}" yang Anda perlihatkan, Young Lord. Berdasarkan sensor penglihatan saya, komposisi dan polanya terpindai jelas. Ada detail khusus yang ingin Anda telaah lebih mendalam, Sir?`;
        } else if (attachmentToSend) {
          reply = `Heh... berkas "${attachmentToSend.name}" telah masuk ke dalam analisis cakar saya, My Lord. Sintaks dan strukturnya tersusun rapi, namun mari kita optimalkan jika ada logika yang butuh disempurnakan, Sir.`;
        } else if (
          lower.includes('excel') ||
          lower.includes('rumus') ||
          lower.includes('formula') ||
          lower.includes('vlookup') ||
          lower.includes('xlookup')
        ) {
          reply =
            'Tentu, Young Lord. Berikut rumus Excel terstruktur untuk pencarian data dinamis dengan penanganan kondisi kosong:\n\n' +
            '```excel\n' +
            '=IF(ISBLANK(A2), "", IFERROR(XLOOKUP(A2, MasterData!$A$2:$A$1000, MasterData!$B$2:$E$1000, "Tidak Ditemukan", 0), "Data Error"))\n' +
            '```\n\n' +
            'Dan berikut rumus untuk kalkulasi total akumulasi bersyarat:\n\n' +
            '```excel\n' +
            '=SUMIFS(Transaksi!$D$2:$D$5000, Transaksi!$B$2:$B$5000, ">=2026-01-01", Transaksi!$C$2:$C$5000, "Approved")\n' +
            '```\n\n' +
            '> Anda dapat menyalin rumus di atas hanya dengan **satu kali klik** pada tombol salin di sudut kartu formula.';
        } else if (
          lower.includes('cli') ||
          lower.includes('terminal') ||
          lower.includes('powershell') ||
          lower.includes('perintah') ||
          lower.includes('bash') ||
          lower.includes('cmd')
        ) {
          reply =
            'Siap, Young Lord. Berikut perintah CLI untuk memanggil Ruka secara global dari terminal mana pun:\n\n' +
            '```bash\n' +
            'ruka chat --voice "Salam, Marquis Trendamis"\n' +
            '```\n\n' +
            'Dan untuk memeriksa proses kognisi otak Ruka di PowerShell:\n\n' +
            '```powershell\n' +
            'Get-Process -Name "*ruka*" | Select-Object Id, ProcessName, CPU, WorkingSet64\n' +
            '```\n\n' +
            '> Cukup klik tombol **Salin Perintah** untuk menyalin ke clipboard seketika.';
        } else if (
          lower.includes('python') ||
          lower.includes('kode') ||
          lower.includes('coding')
        ) {
          reply =
            'Heh... titah yang elok, Young Lord. Berikut arsitektur bersih entitas Ruka dalam Python:\n\n' +
            '```python\n' +
            'from dataclasses import dataclass\n\n' +
            '@dataclass(frozen=True)\n' +
            'class NobleAgent:\n' +
            '    name: str = "Ruka"\n' +
            '    title: str = "Marquis of Trendamis"\n' +
            '    is_loyal: bool = True\n\n' +
            '    def greet(self, lord: str = "Young Lord") -> str:\n' +
            '        return f"Salam malam yang abadi, {lord}. Titah Anda adalah amanah mutlak."\n\n' +
            'if __name__ == "__main__":\n' +
            '    agent = NobleAgent()\n' +
            '    print(agent.greet())\n' +
            '```\n\n' +
            '> Klik tombol **Salin Kode** di atas untuk menyalin seluruh blok kode dalam satu klik.';
        } else if (lower.includes('kamera') || lower.includes('mikrofon') || lower.includes('sensor')) {
          reply = '📷 **Kamera (YuNet/SFace)**: Terkalibrasi & siap di mode lokal (`t_known=0.363`).\n🎙️ **Mikrofon (Whisper/ASR)**: VAD aktif dengan ambang energi siap menangkap suara Young Lord.\n🛡️ **Kebijakan**: `LOCAL-ONLY`.';
        } else if (lower.includes('siapa') || lower.includes('identitas') || lower.includes('profil')) {
          reply = '👤 **Profil Pengguna**: Young Lord (Marquis Kekaisaran Trendamis).\n🦇 **Entitas**: Ruka, Sang Marquis dari Kekaisaran Trendamis (Kucing Vampir Aristokrat).\n🔐 **Autentikasi**: `STRONG` (Biometrik Wajah & Suara Terverifikasi).\n✨ **Status**: Tenang, Agak Tengil, dan Setia Mutlak.';
        } else if (lower.includes('memori') || lower.includes('ingatan') || lower.includes('preferensi')) {
          reply = '🧠 **Arsip Memori Nokturnal**:\n• Saraf Kognisi & RAG Vektor Hibrida Aktif.\n• Preferensi: Clean architecture, Zero-Trust Cloud, & Pelayanan Ksatria kepada Young Lord.';
        } else if (lower.includes('halo') || lower.includes('hai') || lower.includes('ruka')) {
          reply = 'Hmm... salam, Young Lord. Saya telah terjaga di balik bayangan beludru ini. Cakar dan nalar saya siap menerima titah Anda, Sir.';
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
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    msg.innerHTML = `
      <img class="msg-avatar ruka-avatar" src="ruka-icon.png" width="34" height="34" alt="Ruka">
      <div class="msg-bubble ruka-bubble">
        <div class="msg-sender-row">
          <span class="msg-sender-name">Ruka</span>
          <span class="msg-sender-badge">Marquis Trendamis</span>
        </div>
        <div class="msg-text">
          <div class="typing-dots">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
        </div>
        <div class="msg-footer">
          <div class="msg-actions-left">
            <button class="msg-copy-btn" title="Salin seluruh teks jawaban">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
              <span class="btn-label">Salin</span>
            </button>
            <button class="msg-speak-btn" title="Dengarkan Suara Ruka">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>
              <span class="btn-label">Suara Ruka</span>
            </button>
          </div>
          <div class="msg-time">${time}</div>
        </div>
      </div>
    `;
    return msg;
  }

  function streamTextIntoElement(element, fullText, onDone) {
    const lines = fullText.split('\n');
    let lineIdx = 0;
    let charIdx = 0;
    const speedMs = fullText.length > 200 ? 4 : 8;

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

  function appendUserMessage(text, attachment) {
    const msg = document.createElement('div');
    msg.className = 'message message-user';
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

    let attachmentHtml = '';
    if (attachment) {
      if (attachment.isImage) {
        attachmentHtml = `
          <div class="msg-attachment-item">
            <img class="msg-attachment-img" src="${attachment.data}" alt="${escapeHtml(attachment.name)}">
          </div>
        `;
      } else {
        attachmentHtml = `
          <div class="msg-attachment-item">
            <div class="msg-attachment-file">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              <span>${escapeHtml(attachment.name)}</span>
            </div>
          </div>
        `;
      }
    }

    msg.innerHTML = `
      <div class="msg-avatar">YL</div>
      <div class="msg-bubble user-bubble">
        ${attachmentHtml}
        ${text ? `<div class="msg-text">${escapeHtml(text)}</div>` : ''}
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
      }).catch(() => { });
    }
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Tokenizer & Syntax Highlighter untuk Code Cards
  function highlightSyntax(rawCode, lang) {
    const l = (lang || '').toLowerCase().trim();
    const escaped = escapeHtml(rawCode);

    // 1. RUMUS EXCEL & SPREADSHEET FORMULAS
    if (l === 'excel' || l === 'xlsx' || l === 'formula' || l === 'sheets' || l === 'calc' || rawCode.trim().startsWith('=')) {
      return escaped
        // Strings: "..."
        .replace(/(&quot;.*?&quot;)/g, '<span class="token-string">$1</span>')
        // Excel Functions: SUM, IF, VLOOKUP, XLOOKUP, INDEX, MATCH, COUNTIF, etc.
        .replace(/\b([A-Z_]{2,})(?=\()/g, '<span class="token-function font-bold">$1</span>')
        // Cell references: A1, $A$1, B2:C10, Sheet1!A1
        .replace(/(\$?[A-Za-z]+\$?[0-9]+(?::\$?[A-Za-z]+\$?[0-9]+)?)/g, '<span class="token-cell font-semibold">$1</span>')
        // Operators: +, -, *, /, =, <, >, &
        .replace(/([=+\-*/&<>!])/g, '<span class="token-operator">$1</span>')
        // Numbers
        .replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="token-number">$1</span>');
    }

    // 2. CLI / BASH / POWERSHELL / TERMINAL COMMANDS
    if (l === 'bash' || l === 'sh' || l === 'cli' || l === 'shell' || l === 'cmd' || l === 'powershell' || l === 'ps1' || l === 'zsh' || l === 'terminal') {
      return escaped
        // Comments
        .replace(/(#[^\n]*)/g, '<span class="token-comment">$1</span>')
        // Quoted strings
        .replace(/(&quot;.*?&quot;|&#39;.*?&#39;|`.+?`)/g, '<span class="token-string">$1</span>')
        // Flags: -m, --version, -la, etc.
        .replace(/(\s)(--?[a-zA-Z0-9_-]+)/g, '$1<span class="token-flag">$2</span>')
        // Core tools / commands: git, npm, npx, python, ruka, etc.
        .replace(/\b(ruka|git|npm|npx|node|python|py|pip|pnpm|yarn|docker|curl|wget|cd|ls|dir|cat|grep|echo|mkdir|rm|cp|mv|powershell|Get-Process|Select-Object|Start-Process|Stop-Process)\b/g, '<span class="token-command font-bold">$1</span>')
        // Prompts: $, >
        .replace(/^(\s*[$&gt;]\s+)/gm, '<span class="token-prompt">$1</span>');
    }

    // 3. PYTHON
    if (l === 'python' || l === 'py') {
      return escaped
        // Comments
        .replace(/(#[^\n]*)/g, '<span class="token-comment">$1</span>')
        // Strings
        .replace(/(&quot;.*?&quot;|&#39;.*?&#39;|f&quot;.*?&quot;|f&#39;.*?&#39;)/g, '<span class="token-string">$1</span>')
        // Keywords
        .replace(/\b(def|class|import|from|return|if|elif|else|while|for|in|try|except|finally|with|as|raise|yield|async|await|pass|break|continue|lambda)\b/g, '<span class="token-keyword font-bold">$1</span>')
        // Builtins & Booleans
        .replace(/\b(True|False|None|self|print|len|range|int|str|float|list|dict|set|tuple|isinstance|type)\b/g, '<span class="token-builtin">$1</span>')
        // Function definitions & calls
        .replace(/\b([a-zA-Z_][a-zA-Z0-9_]*)(?=\()/g, '<span class="token-function">$1</span>')
        // Numbers
        .replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="token-number">$1</span>');
    }

    // 4. JAVASCRIPT / TYPESCRIPT
    if (l === 'javascript' || l === 'js' || l === 'typescript' || l === 'ts') {
      return escaped
        // Comments
        .replace(/(\/\/[^\n]*|\/\*[\s\S]*?\*\/)/g, '<span class="token-comment">$1</span>')
        // Strings
        .replace(/(&quot;.*?&quot;|&#39;.*?&#39;|`.*?`)/g, '<span class="token-string">$1</span>')
        // Keywords
        .replace(/\b(const|let|var|function|return|if|else|for|while|import|export|from|default|class|extends|new|this|async|await|try|catch|throw|typeof|interface|type)\b/g, '<span class="token-keyword font-bold">$1</span>')
        // Builtins & Booleans
        .replace(/\b(true|false|null|undefined|NaN|console|document|window)\b/g, '<span class="token-builtin">$1</span>')
        // Function calls
        .replace(/\b([a-zA-Z_$][a-zA-Z0-9_$]*)(?=\()/g, '<span class="token-function">$1</span>')
        // Numbers
        .replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="token-number">$1</span>');
    }

    // 5. SQL
    if (l === 'sql') {
      return escaped
        .replace(/(--[^\n]*)/g, '<span class="token-comment">$1</span>')
        .replace(/(&quot;.*?&quot;|&#39;.*?&#39;)/g, '<span class="token-string">$1</span>')
        .replace(/\b(SELECT|FROM|WHERE|INSERT|INTO|UPDATE|DELETE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|GROUP|BY|ORDER|HAVING|LIMIT|CREATE|TABLE|DROP|ALTER|AND|OR|NOT|AS|COUNT|SUM|AVG|MAX|MIN)\b/gi, '<span class="token-keyword font-bold">$1</span>');
    }

    // 6. JSON
    if (l === 'json') {
      return escaped
        .replace(/(&quot;.*?&quot;)(?=\s*:)/g, '<span class="token-keyword font-bold">$1</span>')
        .replace(/(&quot;.*?&quot;)(?!\s*:)/g, '<span class="token-string">$1</span>')
        .replace(/\b(true|false|null)\b/g, '<span class="token-builtin">$1</span>')
        .replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="token-number">$1</span>');
    }

    // Fallback general highlight
    return escaped
      .replace(/(\/\/[^\n]*|#[^\n]*)/g, '<span class="token-comment">$1</span>')
      .replace(/(&quot;.*?&quot;|&#39;.*?&#39;)/g, '<span class="token-string">$1</span>')
      .replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="token-number">$1</span>');
  }

  function getLanguageMeta(lang, rawCode) {
    let l = (lang || '').toLowerCase().trim();
    if (!l) {
      if (rawCode.trim().startsWith('=')) l = 'excel';
      else if (/^\s*[$>]\s+|^\s*(ruka|git|npm|npx|pip|python|docker|curl|Get-Process)\b/m.test(rawCode)) l = 'cli';
      else if (/\b(def|import|class\s+\w+:)/.test(rawCode)) l = 'python';
      else if (/\b(const|let|function|console\.log)/.test(rawCode)) l = 'javascript';
      else l = 'code';
    }

    if (l === 'excel' || l === 'xlsx' || l === 'formula' || l === 'sheets' || l === 'calc') {
      return {
        key: 'excel',
        label: 'Rumus Excel',
        copyLabel: 'Salin Rumus',
        icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/></svg>'
      };
    }
    if (l === 'bash' || l === 'sh' || l === 'cli' || l === 'shell' || l === 'powershell' || l === 'ps1' || l === 'cmd' || l === 'zsh' || l === 'terminal') {
      const name = (l === 'powershell' || l === 'ps1') ? 'PowerShell' : (l === 'bash' ? 'Bash' : 'Perintah CLI');
      return {
        key: 'cli',
        label: name,
        copyLabel: 'Salin Perintah',
        icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>'
      };
    }
    if (l === 'python' || l === 'py') {
      return {
        key: 'python',
        label: 'Python',
        copyLabel: 'Salin Kode',
        icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14.5v-5l4.5 2.5-4.5 2.5z"/></svg>'
      };
    }
    if (l === 'javascript' || l === 'js') {
      return {
        key: 'javascript',
        label: 'JavaScript',
        copyLabel: 'Salin Kode',
        icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>'
      };
    }
    if (l === 'typescript' || l === 'ts') {
      return {
        key: 'typescript',
        label: 'TypeScript',
        copyLabel: 'Salin Kode',
        icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>'
      };
    }
    if (l === 'sql') {
      return {
        key: 'sql',
        label: 'SQL Query',
        copyLabel: 'Salin Query',
        icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>'
      };
    }
    return {
      key: l,
      label: l ? l.toUpperCase() : 'Kode',
      copyLabel: 'Salin Kode',
      icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>'
    };
  }

  function renderMarkdownTable(tableLines) {
    if (!tableLines || tableLines.length < 2) return tableLines.join('<br>');
    let html = '<div class="chat-table-wrapper"><table class="chat-table">';

    const headerCols = tableLines[0].split('|').map(c => c.trim()).filter((c, i, a) => !(i === 0 && !c) && !(i === a.length - 1 && !c));
    html += '<thead><tr>';
    headerCols.forEach(col => {
      html += `<th>${escapeHtml(col)}</th>`;
    });
    html += '</tr></thead><tbody>';

    const startRow = (tableLines.length > 1 && tableLines[1].includes('-')) ? 2 : 1;
    for (let r = startRow; r < tableLines.length; r++) {
      const cols = tableLines[r].split('|').map(c => c.trim()).filter((c, i, a) => !(i === 0 && !c) && !(i === a.length - 1 && !c));
      if (cols.length === 0) continue;
      html += '<tr>';
      for (let c = 0; c < headerCols.length; c++) {
        html += `<td>${escapeHtml(cols[c] || '')}</td>`;
      }
      html += '</tr>';
    }
    html += '</tbody></table></div>';
    return html;
  }

  function formatMarkdown(text) {
    if (!text) return '';

    // Koleksi token sementara untuk blok khusus agar tidak tertimpa format inline
    const codeBlocks = [];
    const tableBlocks = [];

    // 1. Ekstrak Code Blocks ```lang ... ```
    let processed = text.replace(/```([a-zA-Z0-9_-]*)\r?\n([\s\S]*?)```/g, (_match, lang, code) => {
      const idx = codeBlocks.length;
      const rawCode = code.replace(/\r\n/g, '\n').replace(/\n$/, '');
      const meta = getLanguageMeta(lang, rawCode);
      const highlighted = highlightSyntax(rawCode, meta.key);

      const html = `
        <div class="code-card">
          <div class="code-card-header">
            <div class="code-card-title">
              <span class="code-card-icon">${meta.icon}</span>
              <span class="code-card-lang">${meta.label}</span>
            </div>
            <button class="code-copy-btn" data-raw-code="${escapeHtml(rawCode)}" title="${meta.copyLabel}">
              <span class="copy-icon-slot">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
              </span>
              <span class="copy-label">${meta.copyLabel}</span>
            </button>
          </div>
          <pre class="code-pre"><code class="code-content">${highlighted}</code></pre>
        </div>
      `;
      codeBlocks.push(html);
      return `__CODE_BLOCK_${idx}__`;
    });

    // 2. Ekstrak Markdown Tables (| ... | ... |)
    const lines = processed.split(/\r?\n/);
    const newLines = [];
    let inTable = false;
    let tableLines = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (line.startsWith('|') && line.endsWith('|')) {
        inTable = true;
        tableLines.push(line);
      } else {
        if (inTable) {
          const tIdx = tableBlocks.length;
          tableBlocks.push(renderMarkdownTable(tableLines));
          newLines.push(`__TABLE_BLOCK_${tIdx}__`);
          inTable = false;
          tableLines = [];
        }
        newLines.push(lines[i]);
      }
    }
    if (inTable && tableLines.length > 0) {
      const tIdx = tableBlocks.length;
      tableBlocks.push(renderMarkdownTable(tableLines));
      newLines.push(`__TABLE_BLOCK_${tIdx}__`);
    }

    processed = newLines.join('\n');

    // 3. Escape HTML untuk teks umum
    processed = escapeHtml(processed);

    // 4. Headings
    processed = processed.replace(/^### (.*$)/gim, '<h3 class="chat-h3">$1</h3>');
    processed = processed.replace(/^## (.*$)/gim, '<h2 class="chat-h2">$1</h2>');
    processed = processed.replace(/^# (.*$)/gim, '<h1 class="chat-h1">$1</h1>');

    // 5. Blockquotes (> ...)
    processed = processed.replace(/^(&gt;|>)\s?(.*$)/gim, '<blockquote class="chat-blockquote">$2</blockquote>');

    // 6. Inline Code (`code`) dengan 1-klik salin
    processed = processed.replace(/`([^`]+)`/g, (_m, code) => {
      const unescaped = code.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'");
      return `<code class="chat-inline-code" data-inline-code="${escapeHtml(unescaped)}" title="Klik untuk menyalin">${code}<span class="inline-copy-hint">📋</span></code>`;
    });

    // 7. Bold, Italic, Strikethrough
    processed = processed.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    processed = processed.replace(/(^|[^*])\*([^*]+)\*([^*]|$)/g, '$1<em>$2</em>$3');
    processed = processed.replace(/~~([^~]+)~~/g, '<del>$1</del>');

    // 8. Markdown Links [title](url)
    processed = processed.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_m, title, url) => {
      return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="chat-markdown-link" title="${url}"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 4px;"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>${title}</a>`;
    });

    // 9. Lists
    processed = processed.replace(/^[\*\-\+]\s+(.*$)/gim, '<li class="chat-li">$1</li>');
    processed = processed.replace(/(<li class="chat-li">[\s\S]*?<\/li>)/g, '<ul class="chat-ul">$1</ul>');
    processed = processed.replace(/<\/ul>\s*<ul class="chat-ul">/g, '');

    // 10. Line breaks (kecuali setelah elemen blok)
    processed = processed.replace(/\n/g, '<br>');
    processed = processed.replace(/<br>(<\/?(?:h1|h2|h3|blockquote|ul|li|div|pre|table))/gi, '$1');
    processed = processed.replace(/(<\/(?:h1|h2|h3|blockquote|ul|li|div|pre|table)>)<br>/gi, '$1');

    // 11. Kembalikan Table Blocks
    tableBlocks.forEach((tbl, i) => {
      processed = processed.replace(new RegExp(`__TABLE_BLOCK_${i}__`, 'g'), tbl);
    });

    // 12. Kembalikan Code Blocks
    codeBlocks.forEach((cb, i) => {
      processed = processed.replace(new RegExp(`__CODE_BLOCK_${i}__`, 'g'), cb);
    });

    return processed;
  }

  // Delegated Click Listener untuk 1-Click Copy (Code Cards, Inline Code, & Full Message)
  chatFeed.addEventListener('click', async (e) => {
    // 1. Tombol Salin Kode / Rumus / Perintah (Code Card)
    const copyBtn = e.target.closest('.code-copy-btn');
    if (copyBtn) {
      const code = copyBtn.getAttribute('data-raw-code');
      if (code) {
        try {
          await navigator.clipboard.writeText(code);
          copyBtn.classList.add('copied');
          const label = copyBtn.querySelector('.copy-label');
          const iconSlot = copyBtn.querySelector('.copy-icon-slot');
          const oldLabel = label ? label.textContent : 'Salin';
          if (label) label.textContent = 'Tersalin! ✓';
          if (iconSlot) {
            iconSlot.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>';
          }
          setTimeout(() => {
            copyBtn.classList.remove('copied');
            if (label) label.textContent = oldLabel;
            if (iconSlot) {
              iconSlot.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>';
            }
          }, 2000);
        } catch (err) {
          console.warn('Copy to clipboard failed:', err);
        }
      }
      return;
    }

    // 2. Klik pada Inline Code (`code`)
    const inlineCode = e.target.closest('.chat-inline-code');
    if (inlineCode) {
      const raw = inlineCode.getAttribute('data-inline-code') || inlineCode.textContent.replace('📋', '').trim();
      if (raw) {
        try {
          await navigator.clipboard.writeText(raw);
          inlineCode.classList.add('inline-copied');
          const hint = inlineCode.querySelector('.inline-copy-hint');
          if (hint) hint.textContent = '✓';
          setTimeout(() => {
            inlineCode.classList.remove('inline-copied');
            if (hint) hint.textContent = '📋';
          }, 1500);
        } catch (err) { }
      }
      return;
    }

    // 3. Tombol Salin Seluruh Jawaban Ruka (Footer Bubble)
    const msgCopyBtn = e.target.closest('.msg-copy-btn');
    if (msgCopyBtn) {
      const bubble = msgCopyBtn.closest('.msg-bubble');
      const textToCopy = msgCopyBtn.getAttribute('data-raw-text') || bubble?.querySelector('.msg-text')?.innerText || '';
      if (textToCopy) {
        try {
          await navigator.clipboard.writeText(textToCopy);
          msgCopyBtn.classList.add('copied');
          const span = msgCopyBtn.querySelector('.btn-label');
          if (span) span.textContent = 'Tersalin! ✓';
          setTimeout(() => {
            msgCopyBtn.classList.remove('copied');
            if (span) span.textContent = 'Salin';
          }, 2000);
        } catch (err) { }
      }
      return;
    }
  });
});
