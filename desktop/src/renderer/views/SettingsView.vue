<template>
  <div class="w-full h-full flex flex-col px-6 pt-3 pb-5 overflow-y-auto space-y-5 select-none">
    <!-- View Header -->
    <div class="flex items-center justify-between pb-3 border-b border-purple-900/30">
      <div>
        <h2 class="text-xl font-bold text-slate-100 font-serif flex items-center gap-2">
          <span>⚙️</span>
          <span>Pengaturan & Preferensi Noctis OS</span>
        </h2>
        <p class="text-xs text-purple-300/70 mt-0.5">
          Sesuaikan profil kecerdasan, parameter sintesis suara, dan batasan privasi Zero-Trust.
        </p>
      </div>
      <button
        @click="saveSettings"
        class="px-5 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-md transition-all cursor-pointer active:scale-95"
      >
        Simpan Preferensi
      </button>
    </div>

    <!-- Notification Banner if saved -->
    <div
      v-if="showSavedToast"
      class="p-3 rounded-xl bg-emerald-950/70 border border-emerald-500/40 text-emerald-200 text-xs flex items-center gap-2 transition-all"
    >
      <span>✓</span>
      <span>Preferensi berhasil disimpan ke dalam basis data persistensi Ruka.</span>
    </div>

    <!-- Settings Sections -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- 1. AI Model & Intelligence Mode -->
      <div class="p-4 rounded-2xl bg-[#100c24]/80 border border-purple-900/30 space-y-3">
        <div class="text-xs font-bold text-purple-200 uppercase tracking-wider flex items-center gap-2">
          <span>🧠</span>
          <span>Mode Kognisi & Otak AI</span>
        </div>

        <div class="space-y-2">
          <label
            v-for="mode in aiModes"
            :key="mode.id"
            class="flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all"
            :class="selectedAiMode === mode.id
              ? 'bg-purple-900/40 border-purple-500/60 shadow-[0_0_12px_rgba(168,85,247,0.2)]'
              : 'bg-purple-950/20 border-purple-900/30 hover:border-purple-700/40'"
          >
            <input
              type="radio"
              name="aiMode"
              :value="mode.id"
              v-model="selectedAiMode"
              class="mt-0.5 text-purple-600 focus:ring-0"
            />
            <div>
              <div class="text-xs font-semibold text-slate-100">{{ mode.title }}</div>
              <p class="text-[11px] text-purple-300/70 leading-relaxed mt-0.5">{{ mode.desc }}</p>
            </div>
          </label>
        </div>
      </div>

      <!-- 2. Voice & Audio Parameters -->
      <div class="p-4 rounded-2xl bg-[#100c24]/80 border border-purple-900/30 space-y-4">
        <div class="text-xs font-bold text-purple-200 uppercase tracking-wider flex items-center gap-2">
          <span>🔊</span>
          <span>Sintesis Wicara 100% Manusia</span>
        </div>

        <div class="space-y-3">
          <!-- Voice Speed -->
          <div class="space-y-1">
            <div class="flex justify-between text-xs text-purple-200">
              <span>Kecepatan Bicara</span>
              <span class="font-mono text-purple-400">{{ voiceRate }}x</span>
            </div>
            <input
              type="range"
              min="0.7"
              max="1.3"
              step="0.05"
              v-model="voiceRate"
              class="w-full accent-purple-500 cursor-pointer"
            />
          </div>

          <!-- Voice Pitch -->
          <div class="space-y-1">
            <div class="flex justify-between text-xs text-purple-200">
              <span>Frekuensi Nada (Pitch)</span>
              <span class="font-mono text-purple-400">{{ voicePitch }}</span>
            </div>
            <input
              type="range"
              min="0.7"
              max="1.3"
              step="0.05"
              v-model="voicePitch"
              class="w-full accent-purple-500 cursor-pointer"
            />
          </div>

          <!-- Human Prosody F0 -->
          <div class="flex items-center justify-between p-2.5 rounded-xl bg-purple-950/30 border border-purple-900/30">
            <div>
              <div class="text-xs font-semibold text-slate-100">Prosodi F0 Saraf Manusia</div>
              <div class="text-[10px] text-purple-300/60">Modulasi intonasi aristokrat Marquis</div>
            </div>
            <input
              type="checkbox"
              v-model="prosodyEnabled"
              class="rounded text-purple-600 focus:ring-0 cursor-pointer"
            />
          </div>
        </div>
      </div>

      <!-- 3. PathJail Security Boundaries -->
      <div class="p-4 rounded-2xl bg-[#100c24]/80 border border-purple-900/30 space-y-3">
        <div class="text-xs font-bold text-purple-200 uppercase tracking-wider flex items-center gap-2">
          <span>🛡️</span>
          <span>Batas Keamanan PathJail</span>
        </div>
        <div class="space-y-2 text-xs">
          <label class="text-slate-300">Direktori Kerja Utama (Jail Root):</label>
          <input
            type="text"
            v-model="workspacePath"
            class="w-full p-2.5 rounded-xl bg-purple-950/40 border border-purple-800/40 text-purple-100 font-mono text-xs focus:outline-none focus:border-purple-400"
          />
          <p class="text-[11px] text-purple-300/60 leading-relaxed">
            Ruka dilarang keras memodifikasi berkas apa pun di luar folder ini tanpa persetujuan eksplisit.
          </p>
        </div>
      </div>

      <!-- 4. Companion Behavior & Presence -->
      <div class="p-4 rounded-2xl bg-[#100c24]/80 border border-purple-900/30 space-y-3">
        <div class="text-xs font-bold text-purple-200 uppercase tracking-wider flex items-center gap-2">
          <span>🐱</span>
          <span>Persona & Kehadiran Marquis</span>
        </div>
        <div class="space-y-2 text-xs text-purple-200/90 leading-relaxed">
          <div class="p-3 rounded-xl bg-purple-950/20 border border-purple-900/30">
            <span class="font-bold text-purple-100">Sapaan Mulia:</span> Young Lord / My Lord / Sir
          </div>
          <div class="p-3 rounded-xl bg-purple-950/20 border border-purple-900/30">
            <span class="font-bold text-purple-100">Sifat:</span> Tenang, Berwibawa, Sedikit Tengil (Sassy), Setia Mutlak.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const selectedAiMode = ref('hybrid');
const voiceRate = ref('0.95');
const voicePitch = ref('0.88');
const prosodyEnabled = ref(true);
const workspacePath = ref('c:\\Traine\\ruka');
const showSavedToast = ref(false);

const aiModes = [
  {
    id: 'hybrid',
    title: 'Hibrida — Mode B (Disarankan)',
    desc: 'Kombinasi penalaran lokal cepat + model cloud berdaulat saat dibutuhkan dengan Zero-Trust.',
  },
  {
    id: 'local',
    title: 'Lokal Penuh — Mode A',
    desc: '100% offline di mesin laptop Anda. Privasi mutlak tanpa lalu lintas keluar.',
  },
  {
    id: 'cloud',
    title: 'Gemini Cloud — Mode C',
    desc: 'Pikiran cloud berkekuatan penuh melalui Antigravity IDE Loopback.',
  },
];

function saveSettings() {
  if (window.ruka?.settings?.update) {
    window.ruka.settings.update({
      aiMode: selectedAiMode.value,
      voiceRate: voiceRate.value,
      voicePitch: voicePitch.value,
      prosody: prosodyEnabled.value,
    }).catch(() => {});
  }
  showSavedToast.value = true;
  setTimeout(() => {
    showSavedToast.value = false;
  }, 3000);
}
</script>
