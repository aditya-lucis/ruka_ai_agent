<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md"
  >
    <div
      class="relative w-full max-w-2xl bg-[#0c091d] border border-purple-500/50 rounded-2xl shadow-[0_0_50px_rgba(168,85,247,0.4)] overflow-hidden flex flex-col"
    >
      <!-- Dialog Header -->
      <div class="flex items-center justify-between px-4 py-3 bg-purple-950/60 border-b border-purple-900/40">
        <div class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping"></span>
          <span class="w-2.5 h-2.5 -ml-4.5 rounded-full bg-rose-500"></span>
          <span class="text-xs font-semibold text-purple-200 tracking-wide uppercase">
            Sensor Optik Marquis Trendamis (YuNet + SFace Active)
          </span>
        </div>
        <button
          @click="closeModal"
          class="w-7 h-7 rounded-lg text-purple-300 hover:text-white hover:bg-purple-800/50 flex items-center justify-center text-sm"
        >
          ✕
        </button>
      </div>

      <!-- Video Feed with HUD -->
      <div class="relative w-full aspect-video bg-black overflow-hidden flex items-center justify-center">
        <video
          ref="videoRef"
          autoplay
          playsinline
          muted
          class="w-full h-full object-cover scale-x-[-1]"
        ></video>
        <canvas ref="canvasRef" class="hidden"></canvas>

        <!-- HUD Graphic Overlay -->
        <div class="absolute inset-0 pointer-events-none p-6 flex flex-col justify-between">
          <!-- Corners -->
          <div class="flex justify-between">
            <div class="w-6 h-6 border-t-2 border-l-2 border-cyan-400"></div>
            <div class="w-6 h-6 border-t-2 border-r-2 border-cyan-400"></div>
          </div>

          <!-- Central Crosshair / Reticle -->
          <div class="self-center relative w-24 h-24 border border-cyan-400/40 rounded-full flex items-center justify-center">
            <div class="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-ping"></div>
            <div class="absolute inset-0 border-t border-b border-cyan-400/30 scale-75"></div>
            <div class="absolute inset-0 border-l border-r border-cyan-400/30 scale-75"></div>
          </div>

          <!-- Bottom Telemetry & Bottom Corners -->
          <div class="flex items-end justify-between">
            <div class="w-6 h-6 border-b-2 border-l-2 border-cyan-400"></div>

            <div class="text-[10px] font-mono text-cyan-300/80 bg-black/60 px-3 py-1 rounded border border-cyan-500/30 flex gap-4">
              <span>FOV: 78°</span>
              <span>OPTIC: LOCAL-ONLY</span>
              <span>SFACE: 128-d</span>
            </div>

            <div class="w-6 h-6 border-b-2 border-r-2 border-cyan-400"></div>
          </div>
        </div>
      </div>

      <!-- Dialog Footer -->
      <div class="flex items-center justify-between px-4 py-3 bg-purple-950/40 border-t border-purple-900/30">
        <span class="text-xs text-purple-300/70">
          Arahkan ke wajah, dokumen, objek, atau kode untuk diteliti Ruka
        </span>
        <button
          @click="captureSnapshot"
          class="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 shadow-[0_0_15px_rgba(168,85,247,0.4)] active:scale-95 transition-all"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M19 4h-3.17L14.6 2H9.4L8.17 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2z" />
          </svg>
          <span>Ambil Foto & Berikan ke Ruka</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue';

const props = defineProps<{
  isOpen: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'snapshot', attachment: any): void;
}>();

const videoRef = ref<HTMLVideoElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);
let stream: MediaStream | null = null;

watch(
  () => props.isOpen,
  async (open) => {
    if (open) {
      await startCamera();
    } else {
      stopCamera();
    }
  }
);

async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
      audio: false,
    });
    if (videoRef.value) {
      videoRef.value.srcObject = stream;
      await videoRef.value.play();
    }
  } catch (err: any) {
    alert(`Tidak dapat mengakses kamera: ${err.message}`);
    emit('close');
  }
}

function stopCamera() {
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
    stream = null;
  }
  if (videoRef.value) {
    videoRef.value.srcObject = null;
  }
}

function captureSnapshot() {
  if (!videoRef.value || !canvasRef.value) return;

  const video = videoRef.value;
  const canvas = canvasRef.value;
  canvas.width = video.videoWidth || 1280;
  canvas.height = video.videoHeight || 720;

  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  // Mirror effect matches live preview
  ctx.save();
  ctx.scale(-1, 1);
  ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
  ctx.restore();

  const dataUrl = canvas.toDataURL('image/jpeg', 0.88);
  const filename = `snapshot_optik_${new Date().toISOString().slice(11, 19).replace(/:/g, '')}.jpg`;
  const sizeKB = Math.round((dataUrl.length * 0.75) / 1024);

  emit('snapshot', {
    type: 'image',
    isImage: true,
    name: filename,
    mime_type: 'image/jpeg',
    data: dataUrl,
    sizeStr: `${sizeKB} KB`,
  });

  closeModal();
}

function closeModal() {
  stopCamera();
  emit('close');
}

onUnmounted(() => {
  stopCamera();
});
</script>
