<template>
  <div
    class="relative w-full h-full flex flex-col items-center justify-between px-6 pt-1 pb-3 overflow-hidden select-none"
    @mousemove="handleMouseMove"
  >
    <!-- Sanctuary Ambient Atmosphere (Candlelight & Arcane Violet Vignettes) -->
    <div class="absolute inset-0 pointer-events-none">
      <!-- Left candlelight warm glow (mirroring ancient observatory books & candles) -->
      <div class="absolute top-[20%] left-[5%] w-72 h-72 rounded-full bg-amber-500/10 blur-[100px]"></div>
      <!-- Right celestial violet halo -->
      <div class="absolute top-[25%] right-[8%] w-80 h-80 rounded-full bg-purple-600/15 blur-[120px]"></div>
      <!-- Radial central aura -->
      <div class="absolute top-[35%] left-1/2 -translate-x-1/2 -translate-y-1/2 w-[650px] h-[500px] bg-indigo-900/15 blur-[140px]"></div>
    </div>

    <!-- Three.js Visual Arcane Circle & Starlight Particles in background -->
    <ThreeCanvas
      :is-speaking="isSpeaking"
      :is-recording="isRecording"
      :mouse-parallax="mouseCoords"
    />

    <!-- Sanctuary Center Stage -->
    <div class="relative z-10 w-full flex-1 flex flex-col items-center justify-center -mt-1 min-h-0">
      <!-- Interactive Noble Ruka Avatar -->
      <div
        class="relative flex items-center justify-center cursor-pointer group"
        @click="$emit('avatar-click')"
        title="Ruka · Marquis of Trendamis (Klik untuk berinteraksi)"
      >
        <!-- Arcane Aura Ring behind avatar -->
        <div
          class="absolute w-56 h-56 md:w-64 md:h-64 rounded-full border border-purple-500/30 bg-purple-600/10 backdrop-blur-sm pointer-events-none transition-all duration-700 group-hover:scale-105 group-hover:border-purple-400/60"
          :class="isSpeaking 
            ? 'animate-pulse shadow-[0_0_60px_rgba(192,132,252,0.6)] border-purple-300' 
            : 'shadow-[0_0_40px_rgba(168,85,247,0.3)]'"
        ></div>

        <!-- Ruka Pose Image (with Parallax & Breathing) -->
        <div
          class="relative w-48 h-48 sm:w-56 sm:h-56 md:w-60 md:h-60 transition-transform duration-200 ease-out animate-breathe"
          :style="{
            transform: `perspective(800px) rotateY(${avatarTiltX}deg) rotateX(${-avatarTiltY}deg) translateY(${avatarBob}px)`,
          }"
        >
          <img
            src="/ruka-avatar.png"
            alt="Ruka Marquis of Trendamis"
            class="w-full h-full object-contain filter drop-shadow-[0_10px_25px_rgba(0,0,0,0.8)] animate-avatar-glow select-none"
            draggable="false"
          />

          <!-- Eye Glow Sparkles when speaking -->
          <div
            v-if="isSpeaking"
            class="absolute top-[38%] left-[32%] w-3 h-3 bg-fuchsia-400/70 rounded-full blur-sm animate-ping pointer-events-none"
          ></div>
          <div
            v-if="isSpeaking"
            class="absolute top-[38%] right-[32%] w-3 h-3 bg-fuchsia-400/70 rounded-full blur-sm animate-ping pointer-events-none"
          ></div>
        </div>
      </div>

      <!-- Aristocratic Welcome Greeting -->
      <div class="text-center mt-2 max-w-xl px-4 space-y-1">
        <h1
          class="text-xl sm:text-2xl md:text-3xl font-bold tracking-wide text-slate-100 font-serif text-arcane-glow"
        >
          Selamat Datang, Young Lord.
        </h1>
        <p class="text-xs text-purple-200/80 leading-relaxed font-sans max-w-md mx-auto">
          Saya Ruka, Marquis Trendamis. Di sini kita bisa berbicara, belajar, berkarya, dan menjelajah ilmu tanpa batas.
        </p>
      </div>

      <!-- Feature Action Pills -->
      <div class="flex flex-wrap items-center justify-center gap-2 mt-3.5 max-w-2xl px-2">
        <button
          v-for="pill in featurePills"
          :key="pill.id"
          @click="onPillClick(pill)"
          class="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium text-purple-200 bg-[#160f33]/80 hover:bg-purple-900/60 border border-purple-800/40 hover:border-purple-400/60 shadow-sm hover:shadow-[0_0_15px_rgba(168,85,247,0.3)] transition-all cursor-pointer hover:scale-[1.02] active:scale-95"
        >
          <span class="text-sm">{{ pill.icon }}</span>
          <span>{{ pill.label }}</span>
        </button>
      </div>
    </div>

    <!-- Word / TipTap AI Rich Composer Dock -->
    <div class="w-full max-w-4xl relative z-30 shrink-0 mt-2">
      <OrnateInputDock
        :model-value="promptText"
        :is-recording="isRecording"
        :attachment="attachment"
        @update:model-value="$emit('update:prompt-text', $event)"
        @send="$emit('send-prompt')"
        @open-camera="$emit('open-camera')"
        @toggle-recording="$emit('toggle-recording')"
        @attach-file="$emit('attach-file', $event)"
        @remove-attachment="$emit('remove-attachment')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import ThreeCanvas from '../components/ThreeCanvas.vue';
import OrnateInputDock from '../components/OrnateInputDock.vue';

const props = withDefaults(
  defineProps<{
    promptText?: string;
    isSpeaking?: boolean;
    isRecording?: boolean;
    attachment?: any;
  }>(),
  {
    promptText: '',
    isSpeaking: false,
    isRecording: false,
  }
);

const emit = defineEmits<{
  (e: 'update:prompt-text', val: string): void;
  (e: 'send-prompt'): void;
  (e: 'open-camera'): void;
  (e: 'toggle-recording'): void;
  (e: 'attach-file', file: File): void;
  (e: 'remove-attachment'): void;
  (e: 'select-tab', tabId: string): void;
  (e: 'avatar-click'): void;
}>();

const mouseCoords = ref({ x: 0, y: 0 });
const avatarTiltX = ref(0);
const avatarTiltY = ref(0);
const avatarBob = ref(0);

const featurePills = [
  { id: 'chat', label: 'Percakapan & Diskusi', icon: '💬', actionTab: 'chat' },
  { id: 'code', label: 'Coding & Debugging', icon: '</>', actionTab: 'code' },
  { id: 'memory', label: 'Memory Palace & Pengetahuan', icon: '🏛️', actionTab: 'memory' },
  { id: 'tools', label: 'Shadow Hands & Automasi', icon: '🖐️', actionTab: 'tools' },
  { id: 'kernel', label: 'Kernel & Ritme & Produktivitas', icon: '📈', actionTab: 'kernel' },
];

function handleMouseMove(e: MouseEvent) {
  const normX = (e.clientX / window.innerWidth) * 2 - 1;
  const normY = (e.clientY / window.innerHeight) * 2 - 1;
  mouseCoords.value = { x: normX, y: normY };

  avatarTiltX.value = normX * 6;
  avatarTiltY.value = normY * 5;
}

function onPillClick(pill: typeof featurePills[0]) {
  emit('select-tab', pill.actionTab);
}
</script>
