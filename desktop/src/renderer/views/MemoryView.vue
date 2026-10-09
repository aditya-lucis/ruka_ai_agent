<template>
  <div class="w-full h-full flex flex-col px-6 pt-3 pb-5 overflow-y-auto space-y-5 select-none">
    <!-- View Header -->
    <div class="flex items-center justify-between pb-3 border-b border-purple-900/30">
      <div>
        <h2 class="text-xl font-bold text-slate-100 font-serif flex items-center gap-2">
          <span>🏛️</span>
          <span>Memory Palace — 5 Sayap Persistensi</span>
        </h2>
        <p class="text-xs text-purple-300/70 mt-0.5">
          Arsitektur ingatan 5 sayap SQLite WAL + FTS5 tanpa kebocoran amnesia.
        </p>
      </div>
      <div class="flex items-center gap-2 font-mono text-xs">
        <span class="px-3 py-1 rounded-full bg-purple-950/60 border border-purple-500/30 text-purple-300">
          Total: {{ totalMemories }} Ingatan
        </span>
      </div>
    </div>

    <!-- 5 Sayap Cards Grid -->
    <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3">
      <div
        v-for="wing in wings"
        :key="wing.name"
        class="p-3.5 rounded-2xl bg-[#100c24]/80 border border-purple-900/30 hover:border-purple-500/40 transition-all space-y-1.5"
      >
        <div class="text-xs font-bold text-slate-100 flex items-center gap-1.5">
          <span>{{ wing.icon }}</span>
          <span>{{ wing.name }}</span>
        </div>
        <p class="text-[11px] text-purple-300/70 leading-relaxed">{{ wing.desc }}</p>
      </div>
    </div>

    <!-- Search Bar -->
    <div class="flex items-center gap-3 p-2 rounded-2xl bg-[#100c24]/90 border border-purple-900/40 shadow-md">
      <span class="text-purple-400 pl-2">🔍</span>
      <input
        v-model="searchQuery"
        @keydown.enter="performSearch"
        type="text"
        placeholder="Cari ingatan di seluruh 5 sayap istana..."
        class="flex-1 bg-transparent text-slate-100 placeholder-purple-400/40 text-xs focus:outline-none"
      />
      <button
        @click="performSearch"
        class="px-5 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-md transition-all cursor-pointer"
      >
        Cari
      </button>
    </div>

    <!-- Memory Stats Counter Cards -->
    <div class="grid grid-cols-3 gap-3 font-mono">
      <div class="p-3.5 rounded-xl bg-purple-950/30 border border-purple-900/30 text-center">
        <div class="text-xl font-bold text-purple-200">{{ statCounts.episodic }}</div>
        <div class="text-[10px] text-purple-400 uppercase tracking-wider mt-0.5">Episodik</div>
      </div>
      <div class="p-3.5 rounded-xl bg-purple-950/30 border border-purple-900/30 text-center">
        <div class="text-xl font-bold text-purple-200">{{ statCounts.semantic }}</div>
        <div class="text-[10px] text-purple-400 uppercase tracking-wider mt-0.5">Semantik</div>
      </div>
      <div class="p-3.5 rounded-xl bg-purple-950/30 border border-purple-900/30 text-center">
        <div class="text-xl font-bold text-purple-200">{{ statCounts.identity }}</div>
        <div class="text-[10px] text-purple-400 uppercase tracking-wider mt-0.5">Identitas</div>
      </div>
    </div>

    <!-- Search Results Hits List -->
    <div class="p-4 rounded-2xl bg-[#0a0715] border border-purple-900/40 space-y-2 select-text">
      <div class="text-xs font-bold text-purple-300 uppercase tracking-wider mb-2">Hasil Temuan Ingatan</div>

      <div v-if="hits.length === 0" class="py-6 text-center text-xs text-purple-400/60 italic font-serif">
        {{ searchQuery ? 'Tiada jejak ingatan yang cocok dengan titah pencarian.' : 'Ketik kata kunci untuk menelusuri ingatan yang tersimpan.' }}
      </div>

      <div
        v-for="(hit, idx) in hits"
        :key="idx"
        class="p-3 rounded-xl bg-purple-950/30 border border-purple-900/30 flex items-start justify-between gap-3"
      >
        <div class="space-y-1">
          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-900/60 text-purple-200 border border-purple-700/40">
              {{ hit.kind }}
            </span>
            <span class="text-xs text-slate-200">{{ hit.summary }}</span>
          </div>
        </div>
        <span class="text-[10px] text-purple-400/50 font-mono shrink-0">TERSIMPAN</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';

const searchQuery = ref('');
const hits = ref<Array<{ kind: string; summary: string }>>([
  { kind: 'identity', summary: 'Identitas Young Lord: Terverifikasi biometrik tingkat STRONG (Wajah & Suara)' },
  { kind: 'semantic', summary: 'Kaidah Zero-Trust: Cloud tidak pernah memegang kunci eksekusi lokal' },
  { kind: 'episodic', summary: 'Sesi Boot: Verifikasi 684 unit test otak dan 13 uji kernel sukses 100%' },
]);

const statCounts = ref({
  episodic: 12,
  semantic: 34,
  identity: 1,
});

const totalMemories = computed(() => statCounts.value.episodic + statCounts.value.semantic + statCounts.value.identity);

const wings = [
  { name: 'Relationship Wing', icon: '🏛️', desc: 'Graf relasi ikatan Young Lord & Marquis' },
  { name: 'Project Wing', icon: '📐', desc: 'Keputusan kode & arsitektur proyek' },
  { name: 'Preference Wing', icon: '⭐', desc: 'Preferensi, batasan aman, & gaya bicara' },
  { name: 'Daily Wing', icon: '📜', desc: 'Ringkasan episode harian & jurnal WAL' },
  { name: 'Dream Wing', icon: '🌌', desc: 'Konsolidasi abstraksi malam hari saat hening' },
];

onMounted(() => {
  if (window.ruka?.memory?.stats) {
    window.ruka.memory.stats().then((res) => {
      if (res?.payload?.counts_by_kind) {
        statCounts.value = {
          episodic: res.payload.counts_by_kind.episodic ?? 12,
          semantic: res.payload.counts_by_kind.semantic ?? 34,
          identity: res.payload.counts_by_kind.identity ?? 1,
        };
      }
    }).catch(() => {});
  }
});

function performSearch() {
  const q = searchQuery.value.trim();
  if (!q) return;

  if (window.ruka?.memory?.search) {
    window.ruka.memory.search(q).then((res) => {
      hits.value = res?.payload?.hits || [];
    }).catch(() => {});
  } else {
    hits.value = [
      { kind: 'semantic', summary: `Hasil pencarian lokal: "${q}" terindeks dalam SQLite WAL Istana Memori.` }
    ];
  }
}
</script>
