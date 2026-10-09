<template>
  <div class="w-full h-full flex flex-col justify-between px-6 pt-3 pb-5 overflow-hidden">
    <!-- Chat Messages Feed -->
    <div
      ref="feedRef"
      class="flex-1 overflow-y-auto pr-2 space-y-4 mb-4 select-text"
    >
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="w-full flex"
        :class="msg.sender === 'user' ? 'justify-end' : 'justify-start'"
      >
        <!-- System Message -->
        <div
          v-if="msg.sender === 'system'"
          class="w-full text-center my-2"
        >
          <span class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs bg-purple-950/40 border border-purple-800/30 text-purple-300">
            <span>✦</span>
            <span>{{ msg.text }}</span>
          </span>
        </div>

        <!-- User Message Bubble -->
        <div
          v-else-if="msg.sender === 'user'"
          class="max-w-[75%] flex items-start gap-2.5 flex-row-reverse"
        >
          <div class="w-8 h-8 rounded-full bg-gradient-to-tr from-purple-700 to-indigo-600 flex items-center justify-center text-xs font-bold text-white shadow-md shrink-0">
            YL
          </div>
          <div class="p-3.5 rounded-2xl rounded-tr-none bg-gradient-to-r from-purple-900/60 to-indigo-950/70 border border-purple-500/30 text-slate-100 text-sm shadow-md space-y-2">
            <!-- Attachment preview if any -->
            <div
              v-if="msg.attachment"
              class="rounded-lg overflow-hidden border border-purple-400/30 bg-black/40 p-1.5"
            >
              <img
                v-if="msg.attachment.isImage"
                :src="msg.attachment.data"
                :alt="msg.attachment.name"
                class="max-h-56 rounded object-contain"
              />
              <div v-else class="text-xs text-purple-200 flex items-center gap-2 p-1">
                <span>📎</span>
                <span>{{ msg.attachment.name }}</span>
              </div>
            </div>

            <div class="leading-relaxed whitespace-pre-wrap">{{ msg.text }}</div>
            <div class="text-[10px] text-purple-300/60 text-right">{{ msg.time }}</div>
          </div>
        </div>

        <!-- Ruka Message Bubble -->
        <div
          v-else
          class="max-w-[85%] flex items-start gap-3"
        >
          <div class="w-9 h-9 rounded-xl p-[1.5px] bg-gradient-to-tr from-purple-600 to-amber-300 shadow-[0_0_12px_rgba(168,85,247,0.4)] shrink-0 mt-0.5">
            <img
              src="/ruka-avatar.png"
              alt="Ruka"
              class="w-full h-full rounded-xl object-cover bg-black"
            />
          </div>

          <div class="flex-1 p-4 rounded-2xl rounded-tl-none bg-[#120d28]/85 border border-purple-800/40 text-slate-100 text-sm shadow-xl space-y-3">
            <!-- Header row -->
            <div class="flex items-center justify-between pb-1.5 border-b border-purple-900/30">
              <div class="flex items-center gap-2">
                <span class="font-bold text-slate-100 text-xs tracking-wider">Ruka</span>
                <span class="px-2 py-0.5 rounded-full text-[10px] font-medium bg-purple-900/50 text-purple-300 border border-purple-700/40">
                  Marquis Trendamis
                </span>
              </div>
              <span class="text-[10px] text-purple-300/50 font-mono">{{ msg.time }}</span>
            </div>

            <!-- Content Area (Markdown rendered or typing) -->
            <div v-if="msg.isTyping" class="flex items-center gap-2 py-2">
              <span class="w-2 h-2 rounded-full bg-purple-400 animate-ping"></span>
              <span class="w-2 h-2 rounded-full bg-fuchsia-400 animate-pulse"></span>
              <span class="w-2 h-2 rounded-full bg-indigo-400"></span>
              <span class="text-xs text-purple-300/80 italic font-serif ml-2">Merenungkan titah Young Lord...</span>
            </div>

            <div
              v-else
              class="leading-relaxed chat-markdown-content text-slate-200"
              v-html="renderMarkdown(msg.text)"
              @click="handleContentClick"
            ></div>

            <!-- Footer Action Row -->
            <div v-if="!msg.isTyping" class="flex items-center justify-between pt-2 border-t border-purple-900/30 text-xs">
              <div class="flex items-center gap-2">
                <!-- Copy Message Button -->
                <button
                  type="button"
                  @click="copyText(msg.text, $event)"
                  class="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-purple-950/40 hover:bg-purple-900/50 text-purple-300 hover:text-purple-100 transition-colors"
                  title="Salin Seluruh Teks"
                >
                  <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                  <span>Salin</span>
                </button>

                <!-- Speak Button -->
                <button
                  type="button"
                  @click="$emit('speak-message', msg.text)"
                  class="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-purple-950/40 hover:bg-purple-900/50 text-purple-300 hover:text-purple-100 transition-colors"
                  title="Dengarkan Suara Ruka"
                >
                  <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                    <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                  </svg>
                  <span>Suara Ruka</span>
                </button>
              </div>

              <span class="text-[10px] text-purple-400/50 italic">Noble Sovereign Companion</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom Input Dock -->
    <div class="w-full max-w-4xl mx-auto">
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
import { ref, watch, nextTick } from 'vue';
import OrnateInputDock from '../components/OrnateInputDock.vue';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'ruka' | 'system';
  text: string;
  time: string;
  isTyping?: boolean;
  attachment?: any;
}

const props = defineProps<{
  messages: ChatMessage[];
  promptText: string;
  isRecording?: boolean;
  attachment?: any;
}>();

const emit = defineEmits<{
  (e: 'update:prompt-text', val: string): void;
  (e: 'send-prompt'): void;
  (e: 'open-camera'): void;
  (e: 'toggle-recording'): void;
  (e: 'attach-file', file: File): void;
  (e: 'remove-attachment'): void;
  (e: 'speak-message', text: string): void;
}>();

const feedRef = ref<HTMLDivElement | null>(null);

watch(
  () => props.messages,
  () => {
    nextTick(() => {
      if (feedRef.value) {
        feedRef.value.scrollTop = feedRef.value.scrollHeight;
      }
    });
  },
  { deep: true }
);

function escapeHtml(str: string): string {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderMarkdown(raw: string): string {
  if (!raw) return '';

  const codeBlocks: string[] = [];

  // 1. Code blocks
  let processed = raw.replace(/```([a-zA-Z0-9_-]*)\r?\n([\s\S]*?)```/g, (_m, lang, code) => {
    const idx = codeBlocks.length;
    const cleanCode = code.replace(/\r\n/g, '\n').replace(/\n$/, '');
    const l = (lang || '').toLowerCase().trim();

    let label = 'Kode';
    let copyLabel = 'Salin Kode';
    if (l === 'excel' || l === 'formula' || l === 'xlsx') {
      label = 'Rumus Excel';
      copyLabel = 'Salin Rumus';
    } else if (l === 'bash' || l === 'cli' || l === 'powershell' || l === 'shell') {
      label = 'Terminal / CLI';
      copyLabel = 'Salin Perintah';
    } else if (l === 'python') {
      label = 'Python';
    } else if (l === 'javascript' || l === 'js') {
      label = 'JavaScript';
    } else if (l === 'typescript' || l === 'ts') {
      label = 'TypeScript';
    }

    const html = `
      <div class="code-card">
        <div class="code-card-header">
          <div class="flex items-center gap-2">
            <span class="text-purple-400 font-mono font-bold">${label}</span>
          </div>
          <button class="code-copy-btn flex items-center gap-1.5 px-2.5 py-1 rounded bg-purple-900/40 hover:bg-purple-800/60 text-purple-200 text-xs transition-colors cursor-pointer" data-code="${escapeHtml(cleanCode)}">
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            <span class="btn-copy-text">${copyLabel}</span>
          </button>
        </div>
        <pre class="code-pre"><code class="font-mono text-purple-100">${escapeHtml(cleanCode)}</code></pre>
      </div>
    `;
    codeBlocks.push(html);
    return `__CODE_BLOCK_${idx}__`;
  });

  processed = escapeHtml(processed);

  // Bold & Italic
  processed = processed.replace(/\*\*([^*]+)\*\*/g, '<strong class="text-purple-200 font-bold">$1</strong>');
  processed = processed.replace(/(^|[^*])\*([^*]+)\*([^*]|$)/g, '$1<em class="text-purple-300 italic">$2</em>$3');

  // Inline code with click-to-copy
  processed = processed.replace(/`([^`]+)`/g, (_m, c) => {
    const unesc = c.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"');
    return `<code class="chat-inline-code px-1.5 py-0.5 rounded bg-purple-950/70 border border-purple-700/30 text-purple-200 font-mono text-xs cursor-pointer hover:border-purple-400 transition-colors" data-inline="${escapeHtml(unesc)}" title="Klik untuk menyalin">${c} 📋</code>`;
  });

  // Blockquotes
  processed = processed.replace(/^(&gt;|>)\s?(.*$)/gim, '<blockquote class="border-l-2 border-purple-400 pl-3 my-2 text-purple-200/90 italic bg-purple-950/20 py-1 rounded-r">$2</blockquote>');

  // Lists
  processed = processed.replace(/^[\*\-\+]\s+(.*$)/gim, '<li class="ml-4 list-disc text-purple-100">$1</li>');

  // Line breaks
  processed = processed.replace(/\n/g, '<br>');

  // Restore code blocks
  codeBlocks.forEach((cb, i) => {
    processed = processed.replace(new RegExp(`__CODE_BLOCK_${i}__`, 'g'), cb);
  });

  return processed;
}

async function copyText(text: string, e: MouseEvent) {
  try {
    await navigator.clipboard.writeText(text);
    const target = (e.currentTarget as HTMLElement).querySelector('span');
    if (target) {
      const orig = target.textContent;
      target.textContent = 'Tersalin! ✓';
      setTimeout(() => {
        target.textContent = orig;
      }, 1800);
    }
  } catch (_) {}
}

async function handleContentClick(e: MouseEvent) {
  const target = e.target as HTMLElement;

  // Code block copy button
  const copyBtn = target.closest('.code-copy-btn');
  if (copyBtn) {
    const code = copyBtn.getAttribute('data-code');
    if (code) {
      await navigator.clipboard.writeText(code);
      const textSpan = copyBtn.querySelector('.btn-copy-text');
      if (textSpan) {
        const orig = textSpan.textContent;
        textSpan.textContent = 'Tersalin! ✓';
        setTimeout(() => {
          textSpan.textContent = orig;
        }, 1800);
      }
    }
    return;
  }

  // Inline code copy
  const inlineCode = target.closest('.chat-inline-code');
  if (inlineCode) {
    const raw = inlineCode.getAttribute('data-inline');
    if (raw) {
      await navigator.clipboard.writeText(raw);
      const orig = inlineCode.innerHTML;
      inlineCode.innerHTML = `${escapeHtml(raw)} ✓`;
      setTimeout(() => {
        inlineCode.innerHTML = orig;
      }, 1400);
    }
  }
}
</script>
