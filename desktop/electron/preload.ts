/**
 * RUKA — preload. SATU-SATUNYA jembatan renderer -> main.
 * DOC-VERIFIED (tutorial/context-isolation + ipc, Sept 2026):
 *   contextBridge.exposeInMainWorld mengekspos FUNGSI SEMPIT;
 *   ipcRenderer tidak pernah terekspos mentah (dok resmi menyebut
 *   pola `on: ipcRenderer.on` sebagai CONTOH BURUK — kita hanya
 *   mengekspos pembungkus yang memvalidasi argumen).
 *
 * Mengapa tiap fungsi sempit:
 *   runtime.status() — tanpa argumen; tak bisa disalahgunakan.
 *   chat.send(text)  — string dipotong 8000; tipe dicek eksplisit.
 *   memory.search(q) — read-only; tanpa parameter tulis.
 *   tools.execute()  — butuh approval_token dari permissions;
 *                      tanpa token, Python menolak tingkat
 *                      destructive+ (putih-list ganda).
 *   permissions.request() — jalur izin formal; keputusan di sisi
 *                      Python + audit, bukan di renderer.
 *   onStream(cb)     — berlangganan arus; cb dibungkus agar
 *                      halaman tidak menerima objek mentah ipc.
 */

import { contextBridge, ipcRenderer } from 'electron';
import { IPC, Envelope } from './ipc-contract';

const api = {
  runtime: {
    status(): Promise<Envelope> {
      return ipcRenderer.invoke(IPC.RUNTIME_STATUS);
    },
    onStateChange(cb: (state: string) => void): () => void {
      const wrapped = (_e: unknown, env: Envelope) => {
        if (env && env.payload) {
          cb(typeof env.payload === 'string' ? env.payload : env.payload.state);
        }
      };
      ipcRenderer.on(IPC.RUNTIME_EVENT, wrapped);
      return () => ipcRenderer.removeListener(IPC.RUNTIME_EVENT, wrapped);
    },
  },
  chat: {
    send(text: string, attachment?: any): Promise<Envelope> {
      if (typeof text !== 'string') {
        throw new TypeError('chat.send menerima string');
      }
      return ipcRenderer.invoke(IPC.CHAT_SEND, text.slice(0, 8000), attachment);
    },
    onStream(cb: (env: Envelope) => void): () => void {
      const wrapped = (_e: unknown, env: Envelope): void => cb(env);
      ipcRenderer.on(IPC.CHAT_STREAM, wrapped);
      return () => ipcRenderer.removeListener(IPC.CHAT_STREAM, wrapped);
    },
  },
  memory: {
    search(query: string): Promise<Envelope> {
      if (typeof query !== 'string') {
        throw new TypeError('memory.search menerima string');
      }
      return ipcRenderer.invoke(IPC.MEMORY_SEARCH, query.slice(0, 2000));
    },
    stats(): Promise<Envelope> {
      return ipcRenderer.invoke(IPC.MEMORY_STATS);
    },
  },
  tools: {
    list(): Promise<Envelope> {
      return ipcRenderer.invoke(IPC.TOOL_LIST);
    },
    execute(
      tool: string,
      params: object,
      approvalToken?: string
    ): Promise<Envelope> {
      if (typeof tool !== 'string' || typeof params !== 'object') {
        throw new TypeError('tools.execute(tool, params, token?)');
      }
      return ipcRenderer.invoke(IPC.TOOL_EXECUTE, tool, params, approvalToken);
    },
  },
  permissions: {
    request(permission: string, reason: string): Promise<Envelope> {
      return ipcRenderer.invoke(
        IPC.PERMISSION_REQUEST,
        String(permission).slice(0, 48),
        String(reason).slice(0, 2000)
      );
    },
  },
  settings: {
    get(): Promise<Envelope> {
      return ipcRenderer.invoke(IPC.SETTINGS_GET);
    },
    update(patch: object): Promise<Envelope> {
      if (typeof patch !== 'object') {
        throw new TypeError('settings.update menerima objek');
      }
      return ipcRenderer.invoke(IPC.SETTINGS_UPDATE, patch);
    },
  },
  voice: {
    transcribe(wavBase64: string): Promise<Envelope> {
      if (typeof wavBase64 !== 'string') {
        throw new TypeError('voice.transcribe menerima string base64');
      }
      return ipcRenderer.invoke(IPC.VOICE_TRANSCRIBE, wavBase64);
    },
    synthesize(params: string | { text: string; valence?: number; arousal?: number }): Promise<Envelope> {
      const payload = typeof params === 'string' ? { text: params } : params;
      return ipcRenderer.invoke(IPC.VOICE_SYNTHESIZE, payload);
    },
  },
  search: {
    google(query: string, maxResults = 5): Promise<Envelope> {
      if (typeof query !== 'string') {
        throw new TypeError('search.google menerima parameter string query');
      }
      return ipcRenderer.invoke(IPC.GOOGLE_SEARCH, { query, max_results: maxResults });
    },
  },
};

contextBridge.exposeInMainWorld('ruka', api);

contextBridge.exposeInMainWorld('electronAPI', {
  minimize: () => ipcRenderer.invoke('window:minimize'),
  maximize: () => ipcRenderer.invoke('window:maximize'),
  isMaximized: () => ipcRenderer.invoke('window:is-maximized'),
  close: () => ipcRenderer.invoke('window:close'),
  onMaximizeChange: (cb: (isMax: boolean) => void) => {
    const wrapped = (_e: unknown, isMax: boolean) => cb(isMax);
    ipcRenderer.on('window:maximize-change', wrapped);
    return () => ipcRenderer.removeListener('window:maximize-change', wrapped);
  },
});

