<template>
  <aside
    class="w-60 h-full flex flex-col justify-between py-4 px-3 bg-[#0a0715]/80 backdrop-blur-xl border-r border-purple-900/25 select-none shrink-0 z-20"
  >
    <!-- Navigation List -->
    <div class="space-y-1.5">
      <button
        v-for="item in navItems"
        :key="item.id"
        @click="$emit('select-tab', item.id)"
        class="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all group relative overflow-hidden"
        :class="activeTab === item.id
          ? 'bg-purple-900/50 text-purple-100 shadow-[0_0_15px_rgba(168,85,247,0.25)] border border-purple-500/40'
          : 'text-slate-400 hover:text-purple-200 hover:bg-purple-950/30 border border-transparent'"
      >
        <!-- Active Left Indicator Bar -->
        <span
          v-if="activeTab === item.id"
          class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-gradient-to-b from-purple-400 to-fuchsia-500 rounded-r-full shadow-[0_0_8px_#c084fc]"
        ></span>

        <div class="flex items-center gap-3">
          <span class="text-base" :class="activeTab === item.id ? 'text-purple-300' : 'text-slate-400 group-hover:text-purple-300'">
            {{ item.icon }}
          </span>
          <span class="tracking-wide">{{ item.label }}</span>
        </div>

        <!-- Optional Chevron or Badge -->
        <svg
          v-if="item.hasSubmenu || activeTab === item.id"
          class="w-3.5 h-3.5 text-purple-400/70 group-hover:text-purple-300 transition-transform"
          :class="activeTab === item.id ? 'translate-x-0.5' : ''"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
        >
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </button>
    </div>

    <!-- Bottom Quote / Philosophy -->
    <div class="px-3 py-3 rounded-xl bg-purple-950/20 border border-purple-900/30 text-center">
      <div class="text-[11px] leading-relaxed text-purple-300/80 italic font-serif">
        "Pengetahuan adalah cahaya, Ruka adalah penuntunnya."
      </div>
      <div class="mt-1 text-[10px] text-purple-400/50 tracking-widest uppercase font-semibold">
        ✦ Trendamis Doctrine ✦
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
export interface NavItem {
  id: string;
  label: string;
  icon: string;
  hasSubmenu?: boolean;
}

const props = defineProps<{
  activeTab: string;
}>();

defineEmits<{
  (e: 'select-tab', tabId: string): void;
}>();

const navItems: NavItem[] = [
  { id: 'home', label: 'Beranda', icon: '🏠' },
  { id: 'chat', label: 'Percakapan', icon: '💬', hasSubmenu: true },
  { id: 'code', label: 'Kode', icon: '</>' },
  { id: 'organs', label: 'Matriks Organ', icon: '🪢' },
  { id: 'memory', label: 'Memory Palace', icon: '🏛️' },
  { id: 'tools', label: 'Shadow Hands', icon: '🔧' },
  { id: 'kernel', label: 'Kernel & Ritme', icon: '📈' },
  { id: 'settings', label: 'Pengaturan', icon: '⚙️' },
];
</script>
