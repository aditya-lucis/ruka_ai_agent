<template>
  <div class="h-screen w-screen flex flex-col bg-[#07050e] text-slate-100 overflow-hidden font-sans select-none">
    <!-- Top Header Bar -->
    <TopHeader
      :voice-enabled="voiceEnabled"
      :presence-mode-text="presenceModeText"
      :lunar-phase-name="lunarPhaseName"
      :lunar-icon="lunarIcon"
      @toggle-voice="toggleVoice"
    />

    <!-- Main 3-Column Body -->
    <div class="flex-1 flex overflow-hidden relative">
      <!-- Left Sidebar Navigation -->
      <LeftSidebar
        :active-tab="activeTab"
        @select-tab="handleSelectTab"
      />

      <!-- Center Dynamic View Stage -->
      <main class="flex-1 relative overflow-hidden bg-gradient-to-b from-[#0c091d]/40 via-[#07050e] to-[#07050e]">
        <!-- Home View (The Arcane Sanctuary) -->
        <HomeView
          v-if="activeTab === 'home'"
          :prompt-text="promptText"
          :is-speaking="isSpeaking"
          :is-recording="isRecording"
          :attachment="currentAttachment"
          @update:prompt-text="promptText = $event"
          @send-prompt="sendCurrentPrompt"
          @open-camera="isCameraOpen = true"
          @toggle-recording="toggleRecording"
          @attach-file="handleAttachFile"
          @remove-attachment="currentAttachment = null"
          @select-tab="handleSelectTab"
          @avatar-click="onAvatarInteract"
        />

        <!-- Chat View (Conversation & Code Realization) -->
        <ChatView
          v-else-if="activeTab === 'chat'"
          :messages="messages"
          :prompt-text="promptText"
          :is-recording="isRecording"
          :attachment="currentAttachment"
          @update:prompt-text="promptText = $event"
          @send-prompt="sendCurrentPrompt"
          @open-camera="isCameraOpen = true"
          @toggle-recording="toggleRecording"
          @attach-file="handleAttachFile"
          @remove-attachment="currentAttachment = null"
          @speak-message="speakText"
        />

        <!-- Code View -->
        <CodeView v-else-if="activeTab === 'code'" />

        <!-- 10 Organ Matrix View -->
        <OrgansView v-else-if="activeTab === 'organs'" />

        <!-- Memory Palace View -->
        <MemoryView v-else-if="activeTab === 'memory'" />

        <!-- Shadow Hands Tools View -->
        <ToolsView v-else-if="activeTab === 'tools'" />

        <!-- Kernel & Ritme View -->
        <KernelView
          v-else-if="activeTab === 'kernel'"
          :conn-state="connState"
          :lunar-phase-name="lunarPhaseName"
          :lunar-icon="lunarIcon"
          :presence-mode="presenceModeText"
          :log-lines="telemetryLogs"
          @clear-logs="telemetryLogs = []"
        />

        <!-- Settings View -->
        <SettingsView v-else-if="activeTab === 'settings'" />
      </main>

      <!-- Right Sidebar Profile & System Status -->
      <RightSidebar
        :presence-mode-text="presenceModeText"
        :lunar-phase-name="lunarPhaseName"
        :lunar-icon="lunarIcon"
        :voice-enabled="voiceEnabled"
        @select-tab="handleSelectTab"
      />
    </div>

    <!-- Bottom Footer Bar -->
    <footer class="h-6 w-full flex items-center justify-between px-4 bg-[#06040c] border-t border-purple-950/40 text-[10px] text-purple-400/60 font-mono select-none z-30 shrink-0">
      <div class="flex items-center gap-2">
        <span>NOCTIS OS v3.0 · RUKA AI Companion</span>
        <span>•</span>
        <span class="text-purple-300/80">Marquis of Trendamis</span>
      </div>
      <div class="flex items-center gap-3">
        <span>Uptime: aktif</span>
        <span class="flex items-center gap-1 text-emerald-400 font-semibold">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          RUKA Mode: Online
        </span>
      </div>
    </footer>

    <!-- Camera Viewfinder HUD Modal -->
    <CameraModal
      :is-open="isCameraOpen"
      @close="isCameraOpen = false"
      @snapshot="handleCameraSnapshot"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import TopHeader from './components/TopHeader.vue';
import LeftSidebar from './components/LeftSidebar.vue';
import RightSidebar from './components/RightSidebar.vue';
import CameraModal from './components/CameraModal.vue';

// Views
import HomeView from './views/HomeView.vue';
import ChatView, { ChatMessage } from './views/ChatView.vue';
import CodeView from './views/CodeView.vue';
import OrgansView from './views/OrgansView.vue';
import MemoryView from './views/MemoryView.vue';
import ToolsView from './views/ToolsView.vue';
import KernelView from './views/KernelView.vue';
import SettingsView from './views/SettingsView.vue';

// App State
const activeTab = ref<'home' | 'chat' | 'code' | 'organs' | 'memory' | 'tools' | 'kernel' | 'settings'>('home');
const promptText = ref('');
const voiceEnabled = ref(true);
const isSpeaking = ref(false);
const isRecording = ref(false);
const isCameraOpen = ref(false);
const connState = ref('connected');
const presenceModeText = ref('Hibrida (Mode B)');
const lunarPhaseName = ref('Purnama');
const lunarIcon = ref('🌙');
const currentAttachment = ref<any>(null);

// Telemetry Event Logs
const telemetryLogs = ref<Array<{ ts: string; text: string; type?: string }>>([
  { ts: getCurrentTime(), text: '[SYS] Desktop renderer loaded with Vue 3 + Tailwind 4 + Three.js.', type: 'sys' },
  { ts: getCurrentTime(), text: '[KERNEL] Bun OS Kernel EventBus V3 ready on ws://127.0.0.1:8766.', type: 'kernel' },
  { ts: getCurrentTime(), text: '[PRESENCE] Sovereign Companion Model B (Hibrida) activated.', type: 'presence' },
]);

// Chat History Messages
const messages = ref<ChatMessage[]>([
  {
    id: 'sys-1',
    sender: 'system',
    text: 'RUKA Sovereign Companion — Tubuh Desktop Siaga Penuh. Siap mengeksekusi titah, kode, dan instruksi.',
    time: getCurrentTime(),
  },
  {
    id: 'ruka-1',
    sender: 'ruka',
    text: 'Salam takzim, Young Lord. Saya telah terjaga di balik bayangan beludru ini... Seluruh kognisi otonom, sensor visual kamera, mikrofon wicara, kalkulator formula, dan perkakas CLI siap mengeksekusi titah Anda secara instan.\n\nAda hal menarik yang ingin kita telusuri atau kerjakan bersama hari ini, Sir?',
    time: getCurrentTime(),
  },
]);

function getCurrentTime(): string {
  const now = new Date();
  return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
}

function handleSelectTab(tabId: string) {
  activeTab.value = tabId as any;
}

function toggleVoice() {
  voiceEnabled.value = !voiceEnabled.value;
  if (!voiceEnabled.value) {
    stopAllAudio();
  }
}

function onAvatarInteract() {
  const quips = [
    'Heh... Anda memanggil cakar saya, Young Lord? Saya selalu menyimak.',
    'Mata safir ungu ini mengawasi setiap baris logika Anda dengan setia, Sir.',
    'Tenang, My Lord. Selama Anda berpikir, saya akan menjadi penuntunnya.',
  ];
  const chosen = quips[Math.floor(Math.random() * quips.length)];
  speakText(chosen);
}

// =========================================================================
// ATTACHMENT & CAMERA
// =========================================================================
function handleAttachFile(file: File) {
  const isImg = file.type.startsWith('image/');
  const sizeKB = Math.round(file.size / 1024);
  const sizeStr = sizeKB > 1024 ? `${(sizeKB / 1024).toFixed(1)} MB` : `${sizeKB} KB`;

  const reader = new FileReader();
  if (isImg) {
    reader.onload = (e) => {
      currentAttachment.value = {
        type: 'image',
        isImage: true,
        name: file.name,
        mime_type: file.type || 'image/jpeg',
        data: e.target?.result as string,
        sizeStr,
      };
    };
    reader.readAsDataURL(file);
  } else {
    reader.onload = (e) => {
      currentAttachment.value = {
        type: 'file',
        isImage: false,
        name: file.name,
        mime_type: file.type || 'text/plain',
        text_content: e.target?.result as string,
        sizeStr,
      };
    };
    reader.readAsText(file);
  }
}

function handleCameraSnapshot(att: any) {
  currentAttachment.value = att;
}

// =========================================================================
// AUDIO SPEECH SYNTHESIS (TTS) & RECORDING (STT)
// =========================================================================
let currentAudioEl: HTMLAudioElement | null = null;

function stopAllAudio() {
  if (currentAudioEl) {
    currentAudioEl.pause();
    currentAudioEl = null;
  }
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
  isSpeaking.value = false;
}

function cleanTextForVoice(raw: string): string {
  return raw
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/\([^)]*\)/g, ' ')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*[^*]+\*/g, ' ')
    .replace(/_[^_]+_/g, ' ')
    .replace(/[•#~^—]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function speakText(rawText: string) {
  if (!voiceEnabled.value) return;
  stopAllAudio();

  const spoken = cleanTextForVoice(rawText);
  if (!spoken) return;

  isSpeaking.value = true;

  if (window.ruka?.voice?.synthesize) {
    window.ruka.voice.synthesize({ text: spoken })
      .then((res: any) => {
        const audioUrl = res?.payload?.audioUrl;
        if (audioUrl) {
          const audio = new Audio(audioUrl);
          currentAudioEl = audio;
          audio.onended = () => { isSpeaking.value = false; };
          audio.onerror = () => { fallbackBrowserTTS(spoken); };
          audio.play().catch(() => { fallbackBrowserTTS(spoken); });
          return;
        }
        fallbackBrowserTTS(spoken);
      })
      .catch(() => { fallbackBrowserTTS(spoken); });
  } else {
    fallbackBrowserTTS(spoken);
  }
}

function fallbackBrowserTTS(text: string) {
  if (!('speechSynthesis' in window)) {
    isSpeaking.value = false;
    return;
  }
  const ut = new SpeechSynthesisUtterance(text);
  ut.pitch = 0.88;
  ut.rate = 0.95;
  ut.onend = () => { isSpeaking.value = false; };
  ut.onerror = () => { isSpeaking.value = false; };
  window.speechSynthesis.speak(ut);
}

// Microfon recording
let audioStream: MediaStream | null = null;
let audioContext: AudioContext | null = null;
let scriptProcessor: ScriptProcessorNode | null = null;
let recordedSamples: number[] = [];

async function toggleRecording() {
  if (!isRecording.value) {
    try {
      audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      const source = audioContext.createMediaStreamSource(audioStream);
      scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
      recordedSamples = [];
      isRecording.value = true;

      scriptProcessor.onaudioprocess = (e) => {
        if (!isRecording.value) return;
        const data = e.inputBuffer.getChannelData(0);
        for (let i = 0; i < data.length; i++) {
          recordedSamples.push(data[i]);
        }
      };

      source.connect(scriptProcessor);
      scriptProcessor.connect(audioContext.destination);
    } catch (err: any) {
      alert(`Mikrofon tidak dapat diakses: ${err.message}`);
      isRecording.value = false;
    }
  } else {
    isRecording.value = false;
    if (scriptProcessor) scriptProcessor.disconnect();
    if (audioStream) audioStream.getTracks().forEach((t) => t.stop());
    if (audioContext) audioContext.close().catch(() => {});

    if (recordedSamples.length > 4000) {
      // Transcribe via Python Whisper
      const wavBlob = encodeWAV(recordedSamples, 16000);
      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64 = (e.target?.result as string).split(',')[1];
        if (window.ruka?.voice?.transcribe) {
          const resp = await window.ruka.voice.transcribe(base64);
          const recognized = resp?.payload?.text;
          if (recognized && recognized.trim()) {
            promptText.value = recognized.trim();
            sendCurrentPrompt();
          }
        }
      };
      reader.readAsDataURL(wavBlob);
    }
  }
}

function encodeWAV(samples: number[], sampleRate = 16000): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  function writeString(offset: number, string: string) {
    for (let i = 0; i < string.length; i++) view.setUint8(offset + i, string.charCodeAt(i));
  }
  writeString(0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, 'data');
  view.setUint32(40, samples.length * 2, true);
  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([view], { type: 'audio/wav' });
}

// =========================================================================
// SEND PROMPT & CHAT ORCHESTRATION
// =========================================================================
function sendCurrentPrompt() {
  const text = promptText.value.trim();
  const attachment = currentAttachment.value;
  if (!text && !attachment) return;

  // Add User Message
  messages.value.push({
    id: `u-${Date.now()}`,
    sender: 'user',
    text,
    time: getCurrentTime(),
    attachment,
  });

  promptText.value = '';
  currentAttachment.value = null;

  // If on home, automatically switch to chat view to see the response unfolding
  if (activeTab.value === 'home') {
    activeTab.value = 'chat';
  }

  // Add typing bubble for Ruka
  const rukaMsgId = `r-${Date.now()}`;
  messages.value.push({
    id: rukaMsgId,
    sender: 'ruka',
    text: '',
    time: getCurrentTime(),
    isTyping: true,
  });

  const onReplyReceived = (reply: string) => {
    const idx = messages.value.findIndex((m) => m.id === rukaMsgId);
    if (idx !== -1) {
      messages.value[idx].isTyping = false;
      messages.value[idx].text = reply;
    }
    if (voiceEnabled.value) {
      speakText(reply);
    }
  };

  if (window.ruka?.chat?.send) {
    window.ruka.chat.send(text, attachment)
      .then((resp: any) => {
        const delta = resp?.payload?.delta || 'Perintah telah diproses.';
        onReplyReceived(delta);
      })
      .catch((err: any) => {
        onReplyReceived(`[Gagal Komunikasi Otak] ${err.message}`);
      });
  } else {
    // Local noble fallback
    setTimeout(() => {
      let reply = `Heh... titah Anda: "${text}" telah diterima dan diproses dengan setia oleh Ruka, Young Lord. Semua subsistem kognisi dan Shadow Hands siap mengeksekusi langkah berikutnya.`;
      if (text.toLowerCase().includes('excel') || text.toLowerCase().includes('rumus')) {
        reply = 'Tentu, Young Lord. Berikut rumus Excel terstruktur untuk kalkulasi dinamis:\n\n```excel\n=IF(ISBLANK(A2), "", IFERROR(XLOOKUP(A2, MasterData!$A$2:$A$1000, MasterData!$B$2:$E$1000, "Tidak Ditemukan", 0), "Data Error"))\n```\n\n> Klik tombol **Salin Rumus** untuk menyalin ke clipboard seketika.';
      } else if (text.toLowerCase().includes('python') || text.toLowerCase().includes('kode')) {
        reply = 'Titah yang elok, Young Lord. Berikut arsitektur bersih entitas Ruka:\n\n```python\nfrom dataclasses import dataclass\n\n@dataclass(frozen=True)\nclass NobleAgent:\n    name: str = "Ruka"\n    title: str = "Marquis of Trendamis"\n    is_loyal: bool = True\n```';
      }
      onReplyReceived(reply);
    }, 350);
  }
}

// =========================================================================
// LIFECYCLE & KERNEL EVENTBUS INTEGRATION
// =========================================================================
onMounted(() => {
  if (window.ruka?.runtime?.onStateChange) {
    window.ruka.runtime.onStateChange((state: string) => {
      connState.value = state;
      telemetryLogs.value.push({
        ts: getCurrentTime(),
        text: `[RUNTIME] State changed to: ${state}`,
        type: 'runtime',
      });
    });
  }

  if (window.ruka?.kernel?.onEvent) {
    window.ruka.kernel.onEvent((ev: any) => {
      if (!ev || !ev.topic) return;

      // Diurnal Moon Phase
      if (ev.topic.startsWith('lunar.')) {
        const p = ev.payload || {};
        if (p.phase) {
          lunarPhaseName.value = p.phase;
          lunarIcon.value = '🌙';
        }
      }

      // Live log
      telemetryLogs.value.push({
        ts: getCurrentTime(),
        text: `[EVENTBUS] Topic: ${ev.topic} from ${ev.producer || 'kernel'}`,
        type: 'kernel',
      });
    });
  }
});

onUnmounted(() => {
  stopAllAudio();
});
</script>
