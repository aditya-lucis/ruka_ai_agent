<template>
  <div class="w-full relative z-30 select-none">
    <!-- Attachment Preview Bar (if file attached) -->
    <div
      v-if="attachment"
      class="mb-2 px-3 py-2 rounded-xl bg-purple-950/80 border border-purple-500/50 flex items-center justify-between shadow-xl backdrop-blur-md"
    >
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-lg overflow-hidden border border-purple-400/40 flex items-center justify-center bg-black/60 shrink-0">
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
        <div class="min-w-0">
          <div class="text-xs font-semibold text-purple-100 truncate max-w-sm">{{ attachment.name }}</div>
          <div class="text-[10px] text-purple-300/80">{{ attachment.sizeStr }} · Siap di-scan nalar Ruka</div>
        </div>
      </div>
      <button
        @click="$emit('remove-attachment')"
        class="w-6 h-6 rounded-full hover:bg-purple-800/80 text-purple-300 flex items-center justify-center text-sm transition-colors"
        title="Hapus Lampiran"
      >
        ✕
      </button>
    </div>

    <!-- The Ornate Dock & Word/TipTap AI Rich Composer -->
    <div
      class="ornate-dock rounded-2xl border border-purple-700/40 shadow-[0_4px_30px_rgba(0,0,0,0.6)] overflow-hidden transition-all duration-300 bg-[#0e0922]/95 backdrop-blur-xl"
      :class="isExpanded ? 'shadow-[0_0_50px_rgba(168,85,247,0.35)]' : ''"
    >
      <!-- 1. Word / TipTap Style Rich Toolbar Ribbon -->
      <div class="px-3 py-1.5 bg-[#140e2e]/90 border-b border-purple-900/40 flex flex-wrap items-center justify-between gap-1 select-none text-xs">
        <!-- Formatting Tool Buttons Group -->
        <div class="flex items-center flex-wrap gap-0.5">
          <!-- Undo / Redo -->
          <button
            type="button"
            @click="execUndo"
            class="p-1.5 rounded hover:bg-purple-900/50 text-slate-300 hover:text-purple-200 transition-colors"
            title="Urungkan (Undo)"
          >
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 7v6h6" />
              <path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13" />
            </svg>
          </button>

          <span class="w-[1px] h-4 bg-purple-800/40 mx-1"></span>

          <!-- Bold -->
          <button
            type="button"
            @click="applyFormat('bold')"
            class="px-2 py-1 rounded font-bold hover:bg-purple-900/50 text-slate-200 hover:text-white transition-colors"
            title="Tebal (Ctrl+B)"
          >
            B
          </button>

          <!-- Italic -->
          <button
            type="button"
            @click="applyFormat('italic')"
            class="px-2 py-1 rounded italic font-serif hover:bg-purple-900/50 text-slate-200 hover:text-white transition-colors"
            title="Miring (Ctrl+I)"
          >
            I
          </button>

          <!-- Underline -->
          <button
            type="button"
            @click="applyFormat('underline')"
            class="px-2 py-1 rounded underline hover:bg-purple-900/50 text-slate-200 hover:text-white transition-colors"
            title="Garis Bawah (Ctrl+U)"
          >
            U
          </button>

          <!-- Strikethrough -->
          <button
            type="button"
            @click="applyFormat('strike')"
            class="px-2 py-1 rounded line-through hover:bg-purple-900/50 text-slate-200 hover:text-white transition-colors"
            title="Coretan (Strikethrough)"
          >
            S
          </button>

          <span class="w-[1px] h-4 bg-purple-800/40 mx-1"></span>

          <!-- Headings H1, H2 -->
          <button
            type="button"
            @click="applyFormat('h1')"
            class="px-1.5 py-1 rounded font-bold text-[11px] hover:bg-purple-900/50 text-purple-300 hover:text-white transition-colors"
            title="Judul Utama (H1)"
          >
            H1
          </button>
          <button
            type="button"
            @click="applyFormat('h2')"
            class="px-1.5 py-1 rounded font-bold text-[11px] hover:bg-purple-900/50 text-purple-300 hover:text-white transition-colors"
            title="Sub Judul (H2)"
          >
            H2
          </button>

          <span class="w-[1px] h-4 bg-purple-800/40 mx-1"></span>

          <!-- Lists: Bullet, Numbered, Checklist -->
          <button
            type="button"
            @click="applyFormat('list')"
            class="p-1.5 rounded hover:bg-purple-900/50 text-slate-300 hover:text-purple-200 transition-colors"
            title="Daftar Butir (- )"
          >
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" /><line x1="8" y1="18" x2="21" y2="18" />
              <line x1="3" y1="6" x2="3.01" y2="6" /><line x1="3" y1="12" x2="3.01" y2="12" /><line x1="3" y1="18" x2="3.01" y2="18" />
            </svg>
          </button>

          <button
            type="button"
            @click="applyFormat('numbered')"
            class="p-1.5 rounded hover:bg-purple-900/50 text-slate-300 hover:text-purple-200 transition-colors font-mono text-[11px]"
            title="Daftar Nomor (1. )"
          >
            1.
          </button>

          <button
            type="button"
            @click="applyFormat('check')"
            class="p-1.5 rounded hover:bg-purple-900/50 text-slate-300 hover:text-purple-200 transition-colors font-mono text-[11px]"
            title="Daftar Tugas Checklist ([x])"
          >
            ☑
          </button>

          <!-- Blockquote -->
          <button
            type="button"
            @click="applyFormat('quote')"
            class="p-1.5 rounded hover:bg-purple-900/50 text-slate-300 hover:text-purple-200 transition-colors font-serif font-bold text-[12px]"
            title="Kutipan (&gt; )"
          >
            “
          </button>

          <span class="w-[1px] h-4 bg-purple-800/40 mx-1"></span>

          <!-- Inline Code & Code Block -->
          <button
            type="button"
            @click="applyFormat('code')"
            class="px-1.5 py-1 rounded font-mono text-[11px] hover:bg-purple-900/50 text-purple-300 hover:text-purple-100 transition-colors"
            title="Kode Segaris (`kode`)"
          >
            &lt;/&gt;
          </button>

          <button
            type="button"
            @click="applyFormat('codeblock')"
            class="p-1.5 rounded hover:bg-purple-900/50 text-purple-300 hover:text-purple-100 transition-colors"
            title="Blok Kode (```)"
          >
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <polyline points="9 8 5 12 9 16" /><polyline points="15 8 19 12 15 16" />
            </svg>
          </button>

          <!-- Excel Formula Preset -->
          <button
            type="button"
            @click="insertTemplate('excel')"
            class="px-1.5 py-1 rounded font-bold text-[11px] text-emerald-300 hover:bg-emerald-950/60 hover:text-emerald-200 border border-emerald-800/40 transition-colors"
            title="Sisipkan Rumus Excel / Formula"
          >
            ∑ Excel
          </button>

          <!-- Insert Table -->
          <button
            type="button"
            @click="applyFormat('table')"
            class="p-1.5 rounded hover:bg-purple-900/50 text-slate-300 hover:text-purple-200 transition-colors"
            title="Sisipkan Tabel (3x3)"
          >
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M3 9h18M3 15h18M9 3v18M15 3v18" />
            </svg>
          </button>
        </div>

        <!-- Right Tool Indicators -->
        <div class="flex items-center gap-2.5 ml-auto">
          <!-- Zero-Trust Agentic Pill -->
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-emerald-950/70 border border-emerald-500/40 text-emerald-300 shadow-[0_0_8px_rgba(16,185,129,0.2)]">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Agentic · Zero-Trust</span>
          </span>

          <!-- Character counter -->
          <span
            class="text-[11px] font-mono"
            :class="charCount > 7500 ? 'text-rose-400 font-bold' : 'text-slate-400'"
          >
            {{ charCount }} / 8000
          </span>

          <!-- Expand / Shrink Editor -->
          <button
            type="button"
            @click="isExpanded = !isExpanded"
            class="p-1 rounded text-purple-400 hover:text-white hover:bg-purple-900/50 transition-colors"
            :title="isExpanded ? 'Perkecil Composer' : 'Perbesar (Microsoft Word Mode)'"
          >
            <svg v-if="!isExpanded" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="15 3 21 3 21 9"></polyline>
              <polyline points="9 21 3 21 3 15"></polyline>
              <line x1="21" y1="3" x2="14" y2="10"></line>
              <line x1="3" y1="21" x2="10" y2="14"></line>
            </svg>
            <svg v-else class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="4 14 10 14 10 20"></polyline>
              <polyline points="20 10 14 10 14 4"></polyline>
              <line x1="14" y1="10" x2="21" y2="3"></line>
              <line x1="3" y1="21" x2="10" y2="14"></line>
            </svg>
          </button>
        </div>
      </div>

      <!-- 2. Editor Canvas Area -->
      <div class="p-3.5 flex items-start gap-3">
        <!-- Noble Emblem on left -->
        <div class="relative shrink-0 mt-0.5">
          <div class="w-10 h-10 rounded-xl p-[2px] bg-gradient-to-br from-amber-400 via-purple-500 to-fuchsia-600 shadow-[0_0_15px_rgba(168,85,247,0.4)]">
            <img
              src="/ruka-avatar.png"
              alt="Ruka Emblem"
              class="w-full h-full rounded-xl object-cover bg-black"
            />
          </div>
          <div class="absolute -bottom-1 -right-1 w-2.5 h-2.5 rounded-full bg-emerald-500 border-2 border-black"></div>
        </div>

        <!-- Textarea with rich font and styling -->
        <div class="flex-1 min-w-0">
          <textarea
            ref="textareaRef"
            :value="modelValue"
            @input="onInput"
            @keydown="onKeyDown"
            :rows="isExpanded ? 7 : 2"
            maxlength="8000"
            class="w-full bg-transparent text-slate-100 placeholder-purple-300/40 text-sm focus:outline-none resize-none leading-relaxed font-sans"
            placeholder="Tulis titah, instruksi, rumus formula, atau rancang dokumen dengan Marquis Trendamis... (Enter kirim, Shift+Enter baris baru)"
          ></textarea>

          <!-- Bottom Action Controls -->
          <div class="flex items-center justify-between pt-2.5 border-t border-purple-900/30 mt-1.5">
            <!-- Left Tool Chips -->
            <div class="flex items-center flex-wrap gap-2">
              <!-- File / Image Picker -->
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
                class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-purple-200 bg-purple-950/60 hover:bg-purple-900/80 border border-purple-700/40 transition-all shadow-sm group cursor-pointer active:scale-95"
                title="Lampirkan Gambar atau Berkas Dokumen"
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
                class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-purple-200 bg-purple-950/60 hover:bg-purple-900/80 border border-purple-700/40 transition-all shadow-sm group cursor-pointer active:scale-95"
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
                class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all shadow-sm group cursor-pointer active:scale-95"
                :class="isRecording
                  ? 'bg-rose-900/90 border border-rose-500 text-rose-100 shadow-[0_0_20px_rgba(244,63,94,0.6)] animate-pulse'
                  : 'text-purple-200 bg-purple-950/60 hover:bg-purple-900/80 border border-purple-700/40'"
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

            <!-- Send Button on Right -->
            <button
              type="button"
              @click="handleSend"
              :disabled="!canSend"
              class="flex items-center gap-2 px-6 py-2 rounded-xl text-xs font-bold transition-all shadow-lg select-none"
              :class="canSend
                ? 'bg-gradient-to-r from-purple-600 via-fuchsia-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-[0_0_22px_rgba(168,85,247,0.5)] cursor-pointer active:scale-95'
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
    return;
  }

  // Word shortcuts
  if (e.ctrlKey || e.metaKey) {
    if (e.key.toLowerCase() === 'b') {
      e.preventDefault();
      applyFormat('bold');
    } else if (e.key.toLowerCase() === 'i') {
      e.preventDefault();
      applyFormat('italic');
    } else if (e.key.toLowerCase() === 'u') {
      e.preventDefault();
      applyFormat('underline');
    }
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

function execUndo() {
  document.execCommand('undo');
}

function applyFormat(fmt: string) {
  if (!textareaRef.value) return;
  const el = textareaRef.value;
  const start = el.selectionStart;
  const end = el.selectionEnd;
  const text = el.value;
  const selected = text.substring(start, end);

  let replacement = '';
  let cursorOffset = 0;

  switch (fmt) {
    case 'bold':
      replacement = `**${selected || 'teks tebal'}**`;
      cursorOffset = selected ? replacement.length : 2;
      break;
    case 'italic':
      replacement = `*${selected || 'teks miring'}*`;
      cursorOffset = selected ? replacement.length : 1;
      break;
    case 'underline':
      replacement = `<u>${selected || 'teks'}</u>`;
      cursorOffset = selected ? replacement.length : 3;
      break;
    case 'strike':
      replacement = `~~${selected || 'teks coret'}~~`;
      cursorOffset = selected ? replacement.length : 2;
      break;
    case 'h1':
      replacement = `\n# ${selected || 'Judul Dokumen'}\n`;
      cursorOffset = replacement.length;
      break;
    case 'h2':
      replacement = `\n## ${selected || 'Sub Judul'}\n`;
      cursorOffset = replacement.length;
      break;
    case 'list':
      if (selected.includes('\n')) {
        replacement = selected.split('\n').map(l => `- ${l}`).join('\n');
      } else {
        replacement = `\n- ${selected || 'poin pertama'}\n- poin kedua\n`;
      }
      cursorOffset = replacement.length;
      break;
    case 'numbered':
      if (selected.includes('\n')) {
        replacement = selected.split('\n').map((l, i) => `${i + 1}. ${l}`).join('\n');
      } else {
        replacement = `\n1. ${selected || 'langkah satu'}\n2. langkah dua\n`;
      }
      cursorOffset = replacement.length;
      break;
    case 'check':
      replacement = `\n- [ ] ${selected || 'tugas baru'}\n- [ ] tugas berikutnya\n`;
      cursorOffset = replacement.length;
      break;
    case 'quote':
      replacement = `\n> ${selected || 'kutipan penting'}\n`;
      cursorOffset = replacement.length;
      break;
    case 'code':
      replacement = `\`${selected || 'kode'}\``;
      cursorOffset = selected ? replacement.length : 1;
      break;
    case 'codeblock':
      replacement = `\n\`\`\`python\n${selected || '# tulis kode di sini'}\n\`\`\`\n`;
      cursorOffset = selected ? replacement.length : 12;
      break;
    case 'table':
      replacement = `\n| No | Item | Keterangan |\n|---|---|---|\n| 1 | Data A | Nilai A |\n| 2 | Data B | Nilai B |\n`;
      cursorOffset = replacement.length;
      break;
    default:
      return;
  }

  el.setRangeText(replacement, start, end, 'end');
  emit('update:modelValue', el.value);
  el.focus();
}

function insertTemplate(type: string) {
  if (!textareaRef.value) return;
  const el = textareaRef.value;
  let tpl = '';
  if (type === 'excel') {
    tpl = `Tolong buatkan rumus Excel terstruktur untuk:\n\`\`\`excel\n=IF(ISBLANK(A2), "", IFERROR(XLOOKUP(A2, MasterData!$A$2:$A$1000, MasterData!$B$2:$E$1000, "Tidak Ditemukan", 0), "Data Error"))\n\`\`\`\n`;
  }
  const start = el.selectionStart;
  el.setRangeText(tpl, start, el.selectionEnd, 'end');
  emit('update:modelValue', el.value);
  el.focus();
}
</script>
