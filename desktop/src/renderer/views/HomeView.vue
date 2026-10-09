<template>
  <div
    class="relative w-full h-full flex flex-col items-center justify-between px-6 pt-2 pb-3 overflow-hidden select-none"
    @mousemove="handleMouseMove"
  >
    <!-- Sanctuary Ambient Atmosphere (Candlelight & Arcane Violet Vignettes) -->
    <div class="absolute inset-0 pointer-events-none">
      <!-- Left candlelight warm glow -->
      <div class="absolute top-[22%] left-[6%] w-72 h-72 rounded-full bg-amber-500/10 blur-[100px]"></div>
      <!-- Right celestial violet halo -->
      <div class="absolute top-[25%] right-[8%] w-80 h-80 rounded-full bg-purple-600/15 blur-[120px]"></div>
      <!-- Central deep violet aura -->
      <div class="absolute top-[35%] left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[520px] bg-indigo-900/15 blur-[140px]"></div>
    </div>

    <!-- Three.js Visual Arcane Circle & Starlight Particles in background -->
    <ThreeCanvas
      :is-speaking="isSpeaking"
      :is-recording="isRecording"
      :mouse-parallax="mouseCoords"
    />

    <!-- Sanctuary Center Stage (Clean, Spacious, No Pills) -->
    <div class="relative z-10 w-full flex-1 flex flex-col items-center justify-center my-auto min-h-0">
      <!-- Interactive Noble Ruka Avatar -->
      <div
        class="relative flex items-center justify-center cursor-pointer group"
        @click="$emit('avatar-click')"
        title="Ruka · Marquis of Trendamis (Klik untuk berinteraksi)"
      >
        <!-- Arcane Aura Ring behind avatar -->
        <div
          class="absolute w-60 h-60 md:w-68 md:h-68 rounded-full border border-purple-500/30 bg-purple-600/10 backdrop-blur-sm pointer-events-none transition-all duration-700 group-hover:scale-105 group-hover:border-purple-400/60"
          :class="isSpeaking 
            ? 'animate-pulse shadow-[0_0_60px_rgba(192,132,252,0.6)] border-purple-300' 
            : 'shadow-[0_0_40px_rgba(168,85,247,0.3)]'"
        ></div>

        <!-- Ruka Pose Image (with Parallax & Noble Breathing) -->
        <div
          class="relative w-52 h-52 sm:w-60 sm:h-60 md:w-64 md:h-64 transition-transform duration-200 ease-out animate-breathe"
          :style="{
            transform: `perspective(800px) rotateY(${avatarTiltX}deg) rotateX(${-avatarTiltY}deg) translateY(${avatarBob}px)`,
          }"
        >
          <img
            src="/ruka-avatar.png"
            alt="Ruka Marquis of Trendamis"
            class="w-full h-full object-contain filter drop-shadow-[0_12px_30px_rgba(0,0,0,0.85)] animate-avatar-glow select-none"
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
      <div class="text-center mt-3 max-w-xl px-4 space-y-1.5">
        <h1
          class="text-2xl sm:text-3xl font-bold tracking-wide text-slate-100 font-serif text-arcane-glow"
        >
          Selamat Datang, Young Lord.
        </h1>
        <p class="text-xs sm:text-sm text-purple-200/90 leading-relaxed font-sans max-w-lg mx-auto">
          Saya Ruka, Marquis Trendamis. Di sini kita bisa berbicara, belajar, berkarya, dan menjelajah ilmu tanpa batas.
        </p>
      </div>
    </div>

    <!-- Word / TipTap AI Rich Composer Dock -->
    <div class="w-full max-w-4xl relative z-30 shrink-0 mt-auto mb-1">
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

defineEmits<{
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

function handleMouseMove(e: MouseEvent) {
  const normX = (e.clientX / window.innerWidth) * 2 - 1;
  const normY = (e.clientY / window.innerHeight) * 2 - 1;
  mouseCoords.value = { x: normX, y: normY };

  avatarTiltX.value = normX * 6;
  avatarTiltY.value = normY * 5;
}
</script>
