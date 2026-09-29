/**
 * RUKA DESKTOP COMPANION — RENDERER LOGIC
 * Interaksi UI via API sempit `window.ruka` (Preload ContextBridge)
 * Fitur: Saling Ngobrol dengan Suara (STT/TTS), Akses Kamera HUD Lokal, & Multimodal Scan Gambar/Berkas
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements: Window & Navigation
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
      } catch (_) {}
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

            audio.onended = () => {
              if (speakBtn) speakBtn.classList.remove('speaking');
              if (currentAudioElement === audio) currentAudioElement = null;
            };

            audio.onerror = (err) => {
              console.warn('[VOICE] Audio playback error:', err);
              if (speakBtn) speakBtn.classList.remove('speaking');
              if (currentAudioElement === audio) currentAudioElement = null;
              appendLog('[VOICE] Gagal memutar audio neural, beralih ke suara lokal.');
              fallbackSpeechSynthesis(spokenText, speakBtn);
            };

            audio.src = audioUrl;
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

  // Pasang listener suara pada bubble pembuka awal
  const initialSpeakBtn = chatFeed.querySelector('.message-ruka .msg-speak-btn');
  if (initialSpeakBtn) {
    initialSpeakBtn.addEventListener('click', () => {
      const text = chatFeed.querySelector('.message-ruka .msg-text')?.innerText || '';
      speakRukaResponse(text, initialSpeakBtn);
    });
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
      audioContext.close().catch(() => {});
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
      // Gantikan indikator mengetik dengan teks jawaban
      const bubbleContainer = typingBubble.querySelector('.ruka-bubble');
      const textEl = typingBubble.querySelector('.msg-text');
      const speakBtn = typingBubble.querySelector('.msg-speak-btn');

      if (textEl) {
        textEl.innerHTML = '';
        streamTextIntoElement(textEl, responseText, () => {
          coreState.textContent = 'Harmoni Penuh';
          coreAura.style.filter = 'drop-shadow(0 0 12px #a6e3a1)';
          chatFeed.scrollTop = chatFeed.scrollHeight;

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
        });
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
        } else if (lower.includes('kamera') || lower.includes('mikrofon') || lower.includes('sensor')) {
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
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
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
        <div class="msg-footer">
          <button class="msg-speak-btn" title="Dengarkan Suara Ruka">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>
          </button>
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
