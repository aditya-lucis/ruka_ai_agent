<template>
  <header
    class="h-12 w-full flex items-center justify-between px-4 bg-[#0a0716]/90 backdrop-blur-md border-b border-purple-900/30 select-none z-50 shrink-0"
    style="-webkit-app-region: drag;"
    @dblclick="handleTitlebarDblClick"
  >
    <!-- Brand Title (Left) -->
    <div class="flex items-center gap-3" style="-webkit-app-region: no-drag;">
      <div class="relative w-7 h-7 rounded-full p-[1.5px] bg-gradient-to-tr from-purple-600 via-fuchsia-400 to-amber-300 shadow-[0_0_12px_rgba(168,85,247,0.5)]">
        <img
          src="/ruka-icon.png"
          alt="Ruka"
          class="w-full h-full rounded-full object-cover bg-black"
        />
        <div class="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-500 rounded-full border-2 border-black animate-pulse"></div>
      </div>
      <div class="flex items-baseline gap-2">
        <span class="font-bold tracking-wider text-sm text-slate-100 font-sans">NOCTIS OS</span>
        <span class="text-xs text-purple-300/70 tracking-wide font-medium">RUKA · MARQUIS OF TRENDAMIS</span>
      </div>
    </div>

    <!-- Status & Controls (Right) -->
    <div class="flex items-center gap-2.5" style="-webkit-app-region: no-drag;">
      <!-- AI Mode Pill -->
      <div
        class="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-950/60 border border-emerald-500/30 text-emerald-300 shadow-[0_0_10px_rgba(16,185,129,0.15)]"
        title="Mode Operasi: Hibrida (Lokal + Cloud WSS + Bot)"
      >
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
        <span class="w-1.5 h-1.5 -ml-3 rounded-full bg-emerald-400"></span>
        <span>{{ presenceModeText }}</span>
      </div>

      <!-- Lunar Phase Pill -->
      <div
        class="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-purple-950/50 border border-purple-500/30 text-purple-200 cursor-pointer hover:bg-purple-900/40 transition-colors shadow-[0_0_10px_rgba(168,85,247,0.15)]"
        :title="`Fase Bulan & Ritme Noctis: ${lunarPhaseName}`"
      >
        <span>{{ lunarIcon }}</span>
        <span>{{ lunarPhaseName }}</span>
      </div>

      <!-- Voice Toggle Button -->
      <button
        @click="$emit('toggle-voice')"
        class="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-all shadow-sm"
        :class="voiceEnabled 
          ? 'bg-purple-900/60 border border-purple-500/40 text-purple-100 hover:bg-purple-800/70 shadow-[0_0_12px_rgba(168,85,247,0.25)]' 
          : 'bg-slate-900/80 border border-slate-700/50 text-slate-400 hover:text-slate-200'"
        :title="voiceEnabled ? 'Suara Ruka: Aktif (Klik untuk membisukan)' : 'Suara Ruka: Bisu (Klik untuk aktifkan)'"
      >
        <svg
          v-if="voiceEnabled"
          class="w-3.5 h-3.5 text-purple-300"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
          <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
        </svg>
        <svg
          v-else
          class="w-3.5 h-3.5 text-slate-500"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
          <line x1="23" y1="9" x2="17" y2="15"></line>
          <line x1="17" y1="9" x2="23" y2="15"></line>
        </svg>
        <span>{{ voiceEnabled ? 'Suara Ruka' : 'Bisu' }}</span>
      </button>

      <!-- Window Action Buttons (Frameless Electron Controls) -->
      <div class="flex items-center ml-2 border-l border-purple-900/40 pl-2 gap-1">
        <!-- Minimize -->
        <button
          @click="minimizeWindow"
          class="w-7 h-7 flex items-center justify-center rounded hover:bg-purple-900/40 text-slate-400 hover:text-slate-100 transition-colors"
          title="Kecilkan"
        >
          <svg class="w-3 h-3" viewBox="0 0 12 12" fill="currentColor">
            <path d="M2 6h8v1H2z" />
          </svg>
        </button>

        <!-- Maximize / Restore -->
        <button
          @click="toggleMaximize"
          class="w-7 h-7 flex items-center justify-center rounded hover:bg-purple-900/40 text-slate-400 hover:text-slate-100 transition-colors"
          :title="isMaximized ? 'Pulihkan Ukuran' : 'Maksimalkan'"
        >
          <svg v-if="!isMaximized" class="w-3 h-3" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.2">
            <rect x="2" y="2" width="8" height="8" rx="1" />
          </svg>
          <svg v-else class="w-3 h-3" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.1">
            <rect x="4" y="2" width="6" height="6" rx="1" />
            <path d="M2 4.5V9a1 1 0 0 0 1 1h4.5" />
          </svg>
        </button>

        <!-- Close to tray -->
        <button
          @click="closeWindow"
          class="w-7 h-7 flex items-center justify-center rounded hover:bg-red-900/60 text-slate-400 hover:text-red-200 transition-colors"
          title="Tutup ke Tray"
        >
          <svg class="w-3 h-3" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.2">
            <path d="M2.5 2.5l7 7m0-7l-7 7" />
          </svg>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

const props = withDefaults(
  defineProps<{
    voiceEnabled?: boolean;
    presenceModeText?: string;
    lunarPhaseName?: string;
    lunarIcon?: string;
  }>(),
  {
    voiceEnabled: true,
    presenceModeText: 'Hibrida (Mode B)',
    lunarPhaseName: 'Purnama',
    lunarIcon: '🌙',
  }
);

defineEmits<{
  (e: 'toggle-voice'): void;
}>();

const isMaximized = ref(false);

onMounted(() => {
  if (window.electronAPI?.isMaximized) {
    window.electronAPI.isMaximized().then((max) => {
      isMaximized.value = max;
    });
  }

  if (window.electronAPI?.onMaximizeChange) {
    window.electronAPI.onMaximizeChange((max) => {
      isMaximized.value = max;
    });
  }
});

function minimizeWindow() {
  window.electronAPI?.minimize?.();
}

async function toggleMaximize() {
  if (window.electronAPI?.maximize) {
    const max = await window.electronAPI.maximize();
    isMaximized.value = max;
  }
}

function closeWindow() {
  window.electronAPI?.close?.();
}

function handleTitlebarDblClick(e: MouseEvent) {
  const target = e.target as HTMLElement;
  if (target.closest('button')) return;
  toggleMaximize();
}
</script>
