<template>
  <div class="w-full h-full flex flex-col px-6 pt-3 pb-5 overflow-y-auto space-y-5 select-text">
    <!-- View Header -->
    <div class="flex items-center justify-between pb-3 border-b border-purple-900/30">
      <div>
        <h2 class="text-xl font-bold text-slate-100 font-serif flex items-center gap-2">
          <span>&lt;/&gt;</span>
          <span>Coding, Refactoring & Terminal Agen</span>
        </h2>
        <p class="text-xs text-purple-300/70 mt-0.5">
          Action-First: Eksekusi perkakas file, git status, dan loop koreksi otonom di balik PathJail.
        </p>
      </div>
      <div class="flex items-center gap-2">
        <span class="px-3 py-1 rounded-full text-xs font-medium bg-purple-950/60 border border-purple-500/30 text-purple-200">
          PathJail: Aktif
        </span>
      </div>
    </div>

    <!-- Quick Command Launcher & Terminal -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <!-- Left: Quick Terminal Shortcuts -->
      <div class="p-4 rounded-2xl bg-[#100c24]/80 border border-purple-900/30 space-y-3">
        <div class="text-xs font-bold text-purple-200 uppercase tracking-wider flex items-center gap-2">
          <span>⚡</span>
          <span>Perintah Cepat CLI</span>
        </div>
        <div class="space-y-2">
          <button
            v-for="cmd in quickCommands"
            :key="cmd.label"
            @click="runCommand(cmd.code)"
            class="w-full p-2.5 rounded-xl bg-purple-950/30 hover:bg-purple-900/40 border border-purple-800/30 hover:border-purple-500/40 text-left transition-all group"
          >
            <div class="text-xs font-semibold text-purple-200 group-hover:text-white">{{ cmd.label }}</div>
            <div class="text-[11px] font-mono text-purple-400/80 truncate mt-0.5">{{ cmd.code }}</div>
          </button>
        </div>
      </div>

      <!-- Right: Live Code & Terminal Output Simulation -->
      <div class="lg:col-span-2 p-4 rounded-2xl bg-[#0a0715] border border-purple-900/40 flex flex-col justify-between shadow-xl">
        <div class="flex items-center justify-between pb-2 border-b border-purple-900/30 mb-2">
          <div class="flex items-center gap-2 text-xs font-mono text-purple-300">
            <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <span>Terminal Ruka — PowerShell / Bash</span>
          </div>
          <button
            @click="terminalOutput = defaultTerminalOutput"
            class="text-[11px] text-purple-400/70 hover:text-purple-200"
          >
            Bersihkan
          </button>
        </div>

        <pre class="font-mono text-xs text-purple-100/90 leading-relaxed overflow-x-auto whitespace-pre-wrap flex-1 max-h-72 p-2 bg-black/40 rounded-lg">{{ terminalOutput }}</pre>

        <!-- Command Runner Input -->
        <div class="mt-3 flex items-center gap-2">
          <span class="font-mono text-purple-400 text-xs font-bold">$</span>
          <input
            v-model="customCommand"
            @keydown.enter="executeCustomCommand"
            type="text"
            placeholder="Ketik instruksi terminal atau kode untuk diuji (Enter jalankan)..."
            class="flex-1 bg-purple-950/40 border border-purple-800/40 rounded-xl px-3 py-1.5 text-xs text-slate-100 placeholder-purple-400/40 focus:outline-none focus:border-purple-400"
          />
          <button
            @click="executeCustomCommand"
            class="px-4 py-1.5 rounded-xl text-xs font-bold bg-purple-700 hover:bg-purple-600 text-white shadow-md transition-all"
          >
            Jalankan
          </button>
        </div>
      </div>
    </div>

    <!-- Active Projects & Files Overview -->
    <div class="p-4 rounded-2xl bg-[#100c24]/80 border border-purple-900/30 space-y-3">
      <div class="text-xs font-bold text-purple-200 uppercase tracking-wider flex items-center justify-between">
        <span class="flex items-center gap-2">
          <span>📂</span>
          <span>Proyek Aktif & Status Git</span>
        </span>
        <span class="text-[11px] font-mono text-emerald-400">repo: ruka_ai_agent (Clean)</span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div class="p-3 rounded-xl bg-purple-950/20 border border-purple-900/30">
          <div class="text-xs font-semibold text-slate-200">Kognisi Otak</div>
          <div class="text-[11px] text-purple-300/70 font-mono mt-1">ruka-agent/ruka_agent/core</div>
          <div class="text-[10px] text-emerald-400 mt-2">684 Test Hijau Lulus</div>
        </div>
        <div class="p-3 rounded-xl bg-purple-950/20 border border-purple-900/30">
          <div class="text-xs font-semibold text-slate-200">Bun OS Kernel</div>
          <div class="text-[11px] text-purple-300/70 font-mono mt-1">noctis/kernel/src</div>
          <div class="text-[10px] text-emerald-400 mt-2">13 Test Kernel Lulus</div>
        </div>
        <div class="p-3 rounded-xl bg-purple-950/20 border border-purple-900/30">
          <div class="text-xs font-semibold text-slate-200">Desktop Electron</div>
          <div class="text-[11px] text-purple-300/70 font-mono mt-1">desktop/src/renderer</div>
          <div class="text-[10px] text-purple-400 mt-2">Vue 3 + Tailwind 4 + Three.js</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const defaultTerminalOutput = `[RUKA-AGENT] Action-First Environment Active
[GIT] Working tree clean, branch: master
[SYSTEM] Zero-Trust PathJail: c:\\Traine\\ruka
[READY] Siap menerima titah kompilasi atau refaktor, Young Lord.`;

const terminalOutput = ref(defaultTerminalOutput);
const customCommand = ref('');

const quickCommands = [
  { label: 'Cek Status Git', code: 'git status --short' },
  { label: 'Uji Klinis Otak Python', code: 'pytest ruka-agent/tests/ -q' },
  { label: 'Uji Bun OS Kernel', code: 'bun test' },
  { label: 'Sensus Proses Ruka', code: 'Get-Process *ruka*' },
];

function runCommand(cmd: string) {
  terminalOutput.value += `\n\n$ ${cmd}\n[EKSEKUSI] Memproses titah "${cmd}"... Berhasil dieksekusi dengan aman.`;
}

function executeCustomCommand() {
  if (!customCommand.value.trim()) return;
  runCommand(customCommand.value.trim());
  customCommand.value = '';
}
</script>
