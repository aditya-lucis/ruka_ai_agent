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
        <span
          class="px-3 py-1 rounded-full border transition-colors"
          :class="kernelConnState === 'connected' ? 'bg-purple-950/60 border-purple-500/30 text-purple-200' : 'bg-rose-950/40 border-rose-800/40 text-rose-300'"
        >
          WS: ws://127.0.0.1:8766 ({{ kernelConnState }})
        </span>
      </div>
    </div>

    <!-- Telemetry Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-3 font-mono">
      <!-- Status Brain Python -->
      <div class="p-3.5 rounded-xl bg-purple-950/25 border border-purple-900/30">
        <div class="text-[10px] text-purple-400 uppercase tracking-wider">Otak (ruka-brain)</div>
        <div
          class="text-sm font-bold mt-1 flex items-center gap-1.5"
          :class="connState === 'connected' ? 'text-emerald-400' : (connState === 'connecting' || connState === 'reconnecting' ? 'text-amber-400' : 'text-rose-400')"
        >
          <span
            class="w-2 h-2 rounded-full"
            :class="connState === 'connected' ? 'bg-emerald-400 animate-pulse' : (connState === 'connecting' || connState === 'reconnecting' ? 'bg-amber-400 animate-ping' : 'bg-rose-500')"
          ></span>
          {{ connState }}
        </div>
      </div>

      <!-- Status Bun Kernel -->
      <div class="p-3.5 rounded-xl bg-purple-950/25 border border-purple-900/30">
        <div class="text-[10px] text-purple-400 uppercase tracking-wider">Bun OS Kernel</div>
        <div
          class="text-sm font-bold mt-1 flex items-center gap-1.5"
          :class="kernelConnState === 'connected' ? 'text-emerald-400' : (kernelConnState === 'connecting' || kernelConnState === 'reconnecting' ? 'text-amber-400' : 'text-rose-400')"
        >
          <span
            class="w-2 h-2 rounded-full"
            :class="kernelConnState === 'connected' ? 'bg-emerald-400 animate-pulse' : (kernelConnState === 'connecting' || kernelConnState === 'reconnecting' ? 'bg-amber-400 animate-ping' : 'bg-rose-500')"
          ></span>
          {{ kernelConnState }}
        </div>
      </div>

      <!-- Fase Ritme Bulan -->
      <div class="p-3.5 rounded-xl bg-purple-950/25 border border-purple-900/30">
        <div class="text-[10px] text-purple-400 uppercase tracking-wider">Fase Ritme Bulan</div>
        <div class="text-sm font-bold text-purple-200 mt-1">
          {{ lunarIcon }} {{ lunarPhaseName }}
        </div>
      </div>

      <!-- Kehadiran (Presence) -->
      <div class="p-3.5 rounded-xl bg-purple-950/25 border border-purple-900/30">
        <div class="text-[10px] text-purple-400 uppercase tracking-wider">Kehadiran (Presence)</div>
        <div class="text-sm font-bold text-purple-200 mt-1">{{ presenceMode }}</div>
      </div>
    </div>

    <!-- Live EventBus Console Log -->
    <div class="p-4 rounded-2xl bg-[#0a0715] border border-purple-900/40 flex-1 flex flex-col justify-between shadow-xl">
      <div class="flex items-center justify-between pb-2 border-b border-purple-900/30 mb-2 font-mono text-xs">
        <div class="flex items-center gap-2 text-purple-300">
          <span
            class="w-2 h-2 rounded-full"
            :class="connState === 'connected' || kernelConnState === 'connected' ? 'bg-purple-400 animate-ping' : 'bg-rose-500'"
          ></span>
          <span>EventBus & Telemetri Stream</span>
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
          <span :class="line.type === 'error' ? 'text-rose-400 font-bold' : (line.type === 'kernel' ? 'text-cyan-300' : (line.type === 'runtime' ? 'text-amber-300' : 'text-purple-200'))">
            {{ line.text }}
          </span>
        </div>
      </div>

      <div class="mt-3 text-[11px] font-mono text-purple-400/60 text-right">
        Status: {{ connState === 'connected' ? 'Otak Aktif' : 'Otak Mati/Mencari' }} · RingBuffer: 64/tick
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const props = withDefaults(
  defineProps<{
    connState?: string;
    kernelConnState?: string;
    lunarPhaseName?: string;
    lunarIcon?: string;
    presenceMode?: string;
    logLines?: Array<{ ts: string; text: string; type?: string }>;
  }>(),
  {
    connState: 'disconnected',
    kernelConnState: 'disconnected',
    lunarPhaseName: 'Purnama',
    lunarIcon: '🌙',
    presenceMode: 'Hibrida (Mode B)',
    logLines: () => [],
  }
);

const emit = defineEmits<{
  (e: 'clear-logs'): void;
}>();

function clearLogs() {
  emit('clear-logs');
}
</script>
