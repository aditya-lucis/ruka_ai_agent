<template>
  <div class="w-full h-full flex flex-col px-6 pt-3 pb-5 overflow-y-auto space-y-5 select-none">
    <!-- View Header -->
    <div class="flex items-center justify-between pb-3 border-b border-purple-900/30">
      <div>
        <h2 class="text-xl font-bold text-slate-100 font-serif flex items-center gap-2">
          <span>📈</span>
          <span>Kernel & Ritme Noctis OS</span>
        </h2>
        <p class="text-xs text-purple-300/70 mt-0.5">
          Bun OS Kernel EventBus V3, siklus diurnal lunar clock, dan telemetri koneksi.
        </p>
      </div>
      <div class="flex items-center gap-2 font-mono text-xs">
        <span class="px-3 py-1 rounded-full bg-purple-950/60 border border-purple-500/30 text-purple-200">
          WS: ws://127.0.0.1:8766
        </span>
      </div>
    </div>

    <!-- Telemetry Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-3 font-mono">
      <div class="p-3.5 rounded-xl bg-purple-950/25 border border-purple-900/30">
        <div class="text-[10px] text-purple-400 uppercase tracking-wider">Status Konektor</div>
        <div class="text-sm font-bold text-emerald-400 mt-1 flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          {{ connState }}
        </div>
      </div>
      <div class="p-3.5 rounded-xl bg-purple-950/25 border border-purple-900/30">
        <div class="text-[10px] text-purple-400 uppercase tracking-wider">Fase Ritme Bulan</div>
        <div class="text-sm font-bold text-purple-200 mt-1">
          {{ lunarIcon }} {{ lunarPhaseName }}
        </div>
      </div>
      <div class="p-3.5 rounded-xl bg-purple-950/25 border border-purple-900/30">
        <div class="text-[10px] text-purple-400 uppercase tracking-wider">Kehadiran (Presence)</div>
        <div class="text-sm font-bold text-purple-200 mt-1">{{ presenceMode }}</div>
      </div>
      <div class="p-3.5 rounded-xl bg-purple-950/25 border border-purple-900/30">
        <div class="text-[10px] text-purple-400 uppercase tracking-wider">Protokol IPC</div>
        <div class="text-sm font-bold text-purple-200 mt-1">Version 2 (JSONL)</div>
      </div>
    </div>

    <!-- Live EventBus Console Log -->
    <div class="p-4 rounded-2xl bg-[#0a0715] border border-purple-900/40 flex-1 flex flex-col justify-between shadow-xl">
      <div class="flex items-center justify-between pb-2 border-b border-purple-900/30 mb-2 font-mono text-xs">
        <div class="flex items-center gap-2 text-purple-300">
          <span class="w-2 h-2 rounded-full bg-purple-400 animate-ping"></span>
          <span>EventBus V3 Live Telemetry Stream</span>
        </div>
        <button
          @click="clearLogs"
          class="text-[11px] text-purple-400/70 hover:text-purple-200"
        >
          Bersihkan Log
        </button>
      </div>

      <div
        ref="logBoxRef"
        class="font-mono text-xs text-purple-200/90 leading-relaxed overflow-y-auto max-h-72 p-2 bg-black/40 rounded-lg space-y-1 select-text"
      >
        <div v-for="(line, idx) in logLines" :key="idx" class="text-slate-300">
          <span class="text-purple-400/60 mr-2">[{{ line.ts }}]</span>
          <span :class="line.type === 'error' ? 'text-rose-400 font-bold' : (line.type === 'kernel' ? 'text-cyan-300' : 'text-purple-200')">
            {{ line.text }}
          </span>
        </div>
      </div>

      <div class="mt-3 text-[11px] font-mono text-purple-400/60 text-right">
        Uptime: aktif · RingBuffer: 64/tick
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const props = withDefaults(
  defineProps<{
    connState?: string;
    lunarPhaseName?: string;
    lunarIcon?: string;
    presenceMode?: string;
    logLines?: Array<{ ts: string; text: string; type?: string }>;
  }>(),
  {
    connState: 'connected',
    lunarPhaseName: 'Purnama',
    lunarIcon: '🌙',
    presenceMode: 'Hibrida (Mode B)',
    logLines: () => [
      { ts: '14:40:02', text: '[SYS] Desktop renderer loaded with Vue 3 + Tailwind 4 + Three.js.', type: 'sys' },
      { ts: '14:40:03', text: '[KERNEL] Bun OS Kernel EventBus V3 ready on ws://127.0.0.1:8766.', type: 'kernel' },
      { ts: '14:40:04', text: '[LUNAR] Lunar Clock synced: Purnama (Full Moon) peak hour.', type: 'lunar' },
      { ts: '14:40:05', text: '[AVATAR] Three.js procedural avatar listening to viseme pulses.', type: 'avatar' },
    ],
  }
);

const emit = defineEmits<{
  (e: 'clear-logs'): void;
}>();

function clearLogs() {
  emit('clear-logs');
}
</script>
