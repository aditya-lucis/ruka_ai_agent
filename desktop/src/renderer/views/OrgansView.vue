<template>
  <div class="w-full h-full flex flex-col px-6 pt-3 pb-5 overflow-y-auto space-y-4 select-none">
    <!-- View Header -->
    <div class="flex items-center justify-between pb-3 border-b border-purple-900/30 shrink-0">
      <div>
        <h2 class="text-xl font-bold text-slate-100 font-serif flex items-center gap-2">
          <span>🪢</span>
          <span>Matriks 10 Organ PROJECT NOCTIS</span>
        </h2>
        <p class="text-xs text-purple-300/70 mt-0.5">
          Sensus telemetri 10 organ otonom, pengawas watchdog 2s (SLA &lt; 3s), dan batas RAM redline 90%.
        </p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <span class="px-3.5 py-1 rounded-full text-xs font-medium bg-emerald-950/70 border border-emerald-500/40 text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.2)]">
          10/10 Organ Hidup (Siaga Penuh)
        </span>
      </div>
    </div>

    <!-- Organ Cards Grid: Balanced 2x5 or 3x3 layout with uniform card heights -->
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3.5">
      <div
        v-for="organ in organs"
        :key="organ.name"
        class="p-4 rounded-2xl bg-[#110c28]/90 border border-purple-900/40 hover:border-purple-500/50 transition-all hover:shadow-[0_0_25px_rgba(168,85,247,0.2)] flex flex-col justify-between space-y-3 group"
      >
        <!-- Card Header -->
        <div class="flex items-start justify-between gap-2">
          <div class="flex items-center gap-2.5 min-w-0">
            <span class="text-2xl p-2 rounded-xl bg-purple-950/60 border border-purple-800/40 shrink-0">{{ organ.icon }}</span>
            <div class="min-w-0">
              <h3 class="text-xs font-bold text-slate-100 group-hover:text-purple-200 transition-colors truncate">{{ organ.name }}</h3>
              <span class="text-[10px] text-purple-400 font-mono block truncate">{{ organ.sub }}</span>
            </div>
          </div>
          <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 whitespace-nowrap shrink-0">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Siaga
          </span>
        </div>

        <!-- Description -->
        <p class="text-[11px] leading-relaxed text-purple-200/80 min-h-[40px]">
          {{ organ.desc }}
        </p>

        <!-- Metrics Footer -->
        <div class="pt-2.5 border-t border-purple-900/30 text-[10px] text-slate-400 flex items-center justify-between font-mono">
          <span>Limit: <strong class="text-purple-200 font-semibold">{{ organ.limit }}</strong></span>
          <span>{{ organ.metricKey }}: <strong class="text-emerald-400 font-semibold">{{ organ.metricVal }}</strong></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const organs = [
  {
    name: 'Crimson Heart',
    sub: 'HeartEval 20/20',
    icon: '🫀',
    desc: 'Perencana otonom & Bayesian LoopGuard (fail-closed timeout 2.0s).',
    limit: '350 MB',
    metricKey: 'Watchdog',
    metricVal: '2.0s',
  },
  {
    name: 'Memory Palace',
    sub: '5 Sayap SQLite',
    icon: '🏛️',
    desc: '5 Sayap ingatan persistensi SQLite WAL & Vector 512-d (Amnesia 20/20).',
    limit: '500 MB',
    metricKey: 'Recovery',
    metricVal: '< 15s',
  },
  {
    name: 'Multimodal Converse',
    sub: 'Prosodi Marquis',
    icon: '🎭',
    desc: 'Dialog full-duplex, prosodi emosi Marquis, dan perutean intent lokal.',
    limit: '400 MB',
    metricKey: 'Latency',
    metricVal: '640ms',
  },
  {
    name: 'Crimson Eyes',
    sub: 'YuNet + SFace',
    icon: '👁️',
    desc: 'Sensor optik lokal YuNet & SFace. Privasi zero-outbound terjamin.',
    limit: '300 MB',
    metricKey: 'SFace',
    metricVal: '128-d',
  },
  {
    name: 'Blood Hearing',
    sub: 'Whisper ASR',
    icon: '👂',
    desc: 'Deteksi wicara Silero VAD & Faster-Whisper. Latensi < 300ms.',
    limit: '200 MB',
    metricKey: 'FalseWake',
    metricVal: '0',
  },
  {
    name: 'Living Avatar',
    sub: 'Three.js WebGL',
    icon: '👤',
    desc: 'Three.js procedural pose, breathing animation, dan viseme single-writer.',
    limit: '250 MB',
    metricKey: 'FPS',
    metricVal: '60 FPS',
  },
  {
    name: 'Shadow Hands',
    sub: '13 Alat PathJail',
    icon: '✋',
    desc: '13 Alat Blood Contract (File, Git, Terminal) di balik PathJail ketat.',
    limit: '200 MB',
    metricKey: 'KillSwitch',
    metricVal: '< 200ms',
  },
  {
    name: 'Cognitive Core',
    sub: 'Bayesian Core',
    icon: '🧠',
    desc: 'Kognisi otonom, intent router, subagents, dan doktrin Marquis.',
    limit: '450 MB',
    metricKey: 'MathMode',
    metricVal: 'Bayes',
  },
  {
    name: 'Astral Forge',
    sub: 'Physics Lab',
    icon: '⚡',
    desc: 'Lab verifikasi drift simulasi < 0.1% dan batas keselamatan > 5%.',
    limit: '300 MB',
    metricKey: 'Drift',
    metricVal: '< 0.1%',
  },
  {
    name: 'Bun OS Kernel',
    sub: 'EventBus V3',
    icon: '🪐',
    desc: 'EventBus V3 WebSocket (ws://127.0.0.1:8766) & Organ Supervisor.',
    limit: '200 MB',
    metricKey: 'BootTime',
    metricVal: '1.16ms',
  },
];
</script>
