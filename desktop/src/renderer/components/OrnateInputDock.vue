<template>
  <div class="w-full relative z-30">
    <!-- Attachment Preview Bar (if file attached) -->
    <div
      v-if="attachment"
      class="mb-2 px-3 py-2 rounded-xl bg-purple-950/70 border border-purple-500/40 flex items-center justify-between shadow-lg backdrop-blur-md"
    >
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-lg overflow-hidden border border-purple-400/30 flex items-center justify-center bg-black/40">
          <img
            v-if="attachment.isImage"
            :src="attachment.data"
            alt="Attachment"
            class="w-full h-full object-cover"
          />
          <svg
            v-else
            class="w-5 h-5 text-purple-300"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
        </div>
        <div>
          <div class="text-xs font-semibold text-purple-100 truncate max-w-xs">{{ attachment.name }}</div>
          <div class="text-[10px] text-purple-300/70">{{ attachment.sizeStr }} · Siap di-scan nalar Ruka</div>
        </div>
      </div>
      <button
        @click="$emit('remove-attachment')"
        class="w-6 h-6 rounded-full hover:bg-purple-800/60 text-purple-300 flex items-center justify-center text-sm"
        title="Hapus Lampiran"
      >
        ✕
      </button>
    </div>

    <!-- The Ornate Dock Card -->
    <div
      class="ornate-dock rounded-2xl p-3.5 transition-all duration-300"
      :class="isExpanded ? 'shadow-[0_0_40px_rgba(168,85,247,0.3)]' : ''"
    >
      <div class="flex items-start gap-3">
        <!-- Medallion on the left -->
        <div class="relative shrink-0 mt-0.5">
          <div class="w-11 h-11 rounded-xl p-[2px] bg-gradient-to-br from-amber-400 via-purple-500 to-fuchsia-600 shadow-[0_0_15px_rgba(168,85,247,0.4)]">
            <img
              src="/ruka-avatar.png"
              alt="Ruka Emblem"
              class="w-full h-full rounded-xl object-cover bg-black"
            />
          </div>
          <div class="absolute -bottom-1 -right-1 w-3 h-3 rounded-full bg-emerald-500 border-2 border-black"></div>
        </div>

        <!-- Input Area and Controls -->
        <div class="flex-1 min-w-0">
          <!-- Top Row: Status pill and character counter -->
          <div class="flex items-center justify-between mb-1.5 text-xs">
            <span class="text-purple-300/60 text-[11px] font-mono tracking-tight">Marquis Prompt Interface</span>
            <div class="flex items-center gap-3">
              <!-- Agentic Pill -->
              <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 shadow-[0_0_8px_rgba(16,185,129,0.2)]">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>Agentic · Zero-Trust</span>
              </span>

              <!-- Counter -->
              <span
                class="text-[11px] font-mono"
                :class="charCount > 7500 ? 'text-rose-400 font-bold' : 'text-slate-400'"
              >
                {{ charCount }} / 8000
              </span>

              <!-- Expand Editor -->
              <button
                @click="isExpanded = !isExpanded"
                class="text-purple-400 hover:text-purple-200 transition-colors p-0.5"
                :title="isExpanded ? 'Perkecil Dock' : 'Perbesar Dock'"
              >
                <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="15 3 21 3 21 9"></polyline>
                  <polyline points="9 21 3 21 3 15"></polyline>
                  <line x1="21" y1="3" x2="14" y2="10"></line>
                  <line x1="3" y1="21" x2="10" y2="14"></line>
                </svg>
              </button>
            </div>
          </div>

          <!-- Textarea -->
          <textarea
            ref="textareaRef"
            :value="modelValue"
            @input="onInput"
            @keydown="onKeyDown"
            :rows="isExpanded ? 5 : 2"
            maxlength="8000"
            class="w-full bg-transparent text-slate-100 placeholder-purple-300/40 text-sm focus:outline-none resize-none leading-relaxed font-sans"
            placeholder="Tulis pesan, instruksi, atau pertanyaanmu di sini... (Enter kirim, Shift+Enter baris baru)"
          ></textarea>

          <!-- Bottom Action Buttons -->
          <div class="flex items-center justify-between pt-2 border-t border-purple-900/30 mt-1">
            <!-- Left chips -->
            <div class="flex items-center gap-2">
              <!-- File / Image Attachment -->
              <input
                ref="fileInputRef"
                type="file"
                class="hidden"
                accept="image/*,.txt,.py,.js,.ts,.json,.md,.html,.css,.csv,.log,.pdf,.c,.cpp"
                @change="onFileSelected"
              />
              <button
                type="button"
                @click="triggerFileSelect"
                class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-purple-200 bg-purple-950/40 hover:bg-purple-900/60 border border-purple-700/30 transition-all shadow-sm group"
                title="Lampirkan Gambar atau Berkas"
              >
                <svg class="w-3.5 h-3.5 text-purple-400 group-hover:text-purple-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                </svg>
                <span>Lampirkan</span>
              </button>

              <!-- Camera Sensor HUD -->
              <button
                type="button"
                @click="$emit('open-camera')"
                class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-purple-200 bg-purple-950/40 hover:bg-purple-900/60 border border-purple-700/30 transition-all shadow-sm group"
                title="Akses Sensor Kamera YuNet & SFace"
              >
                <svg class="w-3.5 h-3.5 text-cyan-400 group-hover:text-cyan-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                  <circle cx="12" cy="13" r="4" />
                </svg>
                <span>Sensor Kamera</span>
              </button>

              <!-- Speech-to-Text Wicara -->
              <button
                type="button"
                @click="$emit('toggle-recording')"
                class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all shadow-sm group"
                :class="isRecording
                  ? 'bg-rose-900/80 border border-rose-500 text-rose-100 shadow-[0_0_15px_rgba(244,63,94,0.5)] animate-pulse'
                  : 'text-purple-200 bg-purple-950/40 hover:bg-purple-900/60 border border-purple-700/30'"
                :title="isRecording ? 'Sedang merekam suara... Klik untuk selesai' : 'Bicara dengan Suara (Whisper ASR)'"
              >
                <svg class="w-3.5 h-3.5 text-amber-400 group-hover:text-amber-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                  <line x1="12" y1="19" x2="12" y2="23" />
                  <line x1="8" y1="23" x2="16" y2="23" />
                </svg>
                <span>{{ isRecording ? 'Merekam...' : 'Wicara' }}</span>
              </button>
            </div>

            <!-- Send button on right -->
            <button
              type="button"
              @click="handleSend"
              :disabled="!canSend"
              class="flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-bold transition-all shadow-lg select-none"
              :class="canSend
                ? 'bg-gradient-to-r from-purple-600 via-fuchsia-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-[0_0_20px_rgba(168,85,247,0.5)] cursor-pointer active:scale-95'
                : 'bg-slate-800/60 text-slate-500 cursor-not-allowed border border-slate-700/30'"
            >
              <span>Kirim</span>
              <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

const props = defineProps<{
  modelValue: string;
  isRecording?: boolean;
  attachment?: any;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', val: string): void;
  (e: 'send'): void;
  (e: 'open-camera'): void;
  (e: 'toggle-recording'): void;
  (e: 'attach-file', file: File): void;
  (e: 'remove-attachment'): void;
}>();

const isExpanded = ref(false);
const fileInputRef = ref<HTMLInputElement | null>(null);
const textareaRef = ref<HTMLTextAreaElement | null>(null);

const charCount = computed(() => (props.modelValue || '').length);
const canSend = computed(() => (props.modelValue && props.modelValue.trim().length > 0) || !!props.attachment);

function onInput(e: Event) {
  const val = (e.target as HTMLTextAreaElement).value;
  emit('update:modelValue', val);
}

function onKeyDown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
}

function handleSend() {
  if (canSend.value) {
    emit('send');
  }
}

function triggerFileSelect() {
  fileInputRef.value?.click();
}

function onFileSelected(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (file) {
    emit('attach-file', file);
  }
}
</script>
