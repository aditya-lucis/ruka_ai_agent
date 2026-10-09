<template>
  <aside
    class="w-72 h-full flex flex-col justify-between py-4 px-3.5 bg-[#0a0715]/80 backdrop-blur-xl border-l border-purple-900/25 select-none shrink-0 z-20 space-y-4 overflow-y-auto"
  >
    <div class="space-y-4">
      <!-- Ruka Profile Card -->
      <div class="p-3.5 rounded-2xl bg-gradient-to-b from-purple-950/40 to-slate-950/60 border border-purple-800/30 shadow-[0_4px_20px_rgba(0,0,0,0.4)]">
        <div class="flex items-center gap-3">
          <div class="relative w-12 h-12 rounded-xl p-[2px] bg-gradient-to-tr from-purple-600 via-fuchsia-400 to-amber-300 shadow-[0_0_15px_rgba(168,85,247,0.4)]">
            <img
              src="/ruka-avatar.png"
              alt="Ruka Portrait"
              class="w-full h-full rounded-xl object-cover bg-black"
            />
            <span class="absolute -bottom-1 -right-1 w-3.5 h-3.5 rounded-full bg-emerald-500 border-2 border-black"></span>
          </div>
          <div>
            <h3 class="text-sm font-bold text-slate-100 tracking-wider">RUKA</h3>
            <p class="text-xs text-purple-300/80 font-medium">Marquis Trendamis</p>
          </div>
        </div>

        <div class="mt-3 p-2.5 rounded-xl bg-purple-950/30 border border-purple-900/40 text-[11px] leading-relaxed text-purple-200/90 italic">
          "Ide besar lahir dari pikiran yang tidak pernah berhenti bertanya."
          <div class="mt-1 text-right text-[10px] text-purple-400 font-semibold not-italic">
            — Ruka 🐾
          </div>
        </div>
      </div>

      <!-- Status Sistem -->
      <div class="p-3.5 rounded-2xl bg-slate-950/40 border border-purple-900/25 space-y-2.5">
        <div class="text-xs font-semibold text-purple-300/80 uppercase tracking-wider">Status Sistem</div>
        
        <div class="space-y-2 text-xs">
          <!-- Mode AI -->
          <div class="flex items-center justify-between py-1 border-b border-purple-900/20">
            <span class="text-slate-400 flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
              Mode AI
            </span>
            <span class="font-medium text-emerald-400 flex items-center gap-1">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              {{ presenceModeText }}
            </span>
          </div>

          <!-- Bulan -->
          <div class="flex items-center justify-between py-1 border-b border-purple-900/20 cursor-pointer hover:text-purple-200" @click="$emit('select-tab', 'kernel')">
            <span class="text-slate-400 flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
              Bulan
            </span>
            <span class="font-medium text-purple-200 flex items-center gap-1">
              {{ lunarIcon }} {{ lunarPhaseName }}
              <svg class="w-3 h-3 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
            </span>
          </div>

          <!-- Suara -->
          <div class="flex items-center justify-between py-1">
            <span class="text-slate-400 flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
              Suara
            </span>
            <span class="font-medium" :class="voiceEnabled ? 'text-purple-300' : 'text-slate-500'">
              {{ voiceEnabled ? 'Aktif 🔊' : 'Bisu 🔇' }}
            </span>
          </div>
        </div>
      </div>

      <!-- Quick Access Links -->
      <div class="p-3.5 rounded-2xl bg-slate-950/40 border border-purple-900/25 space-y-2">
        <div class="text-xs font-semibold text-purple-300/80 uppercase tracking-wider">Quick Access</div>

        <div class="space-y-1">
          <button
            v-for="link in quickLinks"
            :key="link.id"
            @click="$emit('select-tab', link.id)"
            class="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-purple-200 hover:bg-purple-950/40 transition-colors group"
          >
            <div class="flex items-center gap-2">
              <span>{{ link.icon }}</span>
              <span>{{ link.label }}</span>
            </div>
            <svg class="w-3 h-3 text-purple-400 group-hover:translate-x-0.5 transition-transform" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Bottom Wisdom Card -->
    <div class="p-3 rounded-xl bg-purple-950/20 border border-purple-900/30 text-center">
      <div class="text-[11px] leading-relaxed text-purple-300/80 italic font-serif">
        "Selalu ada cara, selama kau masih mau belajar."
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    presenceModeText?: string;
    lunarPhaseName?: string;
    lunarIcon?: string;
    voiceEnabled?: boolean;
  }>(),
  {
    presenceModeText: 'Hibrida (Mode B)',
    lunarPhaseName: 'Purnama',
    lunarIcon: '🌙',
    voiceEnabled: true,
  }
);

defineEmits<{
  (e: 'select-tab', tabId: string): void;
}>();

const quickLinks = [
  { id: 'organs', label: 'Matriks Organ', icon: '🪢' },
  { id: 'memory', label: 'Memory Palace', icon: '🏛️' },
  { id: 'tools', label: 'Shadow Hands', icon: '🔧' },
  { id: 'kernel', label: 'Kernel & Ritme', icon: '📈' },
];
</script>
