/**
 * Kontrak kanal IPC — CERMINAN SATU-SATU dari Python ipc/contract.py.
 * DOC-VERIFIED (docs resmi Electron, September 2026).
 *
 * Aturan besi: renderer TIDAK PERNAH melihat string kanal mentah.
 * Semua lalu-lintas lewat preload yang memetakan fungsi sempit ->
 * kanal terdaftar di sini. String kanal yang tidak ada di tabel ini
 * adalah bug yang gagal saat kompilasi, bukan kejutan saat runtime.
 */

export const IPC = {
  /** UI -> tray/health: status mesin (req/res). */
  RUNTIME_STATUS: 'ruka:runtime-status',
  /** Teks Bos -> arus balasan (stream). */
  CHAT_SEND: 'ruka:chat-send',
  /** Arus token dari main ke renderer (event). */
  CHAT_STREAM: 'ruka:chat-stream',
  /** Pencarian memori (req/res, read-only). */
  MEMORY_SEARCH: 'ruka:memory-search',
  /** Sensus memori (req/res, read-only). */
  MEMORY_STATS: 'ruka:memory-stats',
  /** Daftar alat + izin (req/res). */
  TOOL_LIST: 'ruka:tool-list',
  /** Eksekusi alat (req/res, butuh approval_token). */
  TOOL_EXECUTE: 'ruka:tool-execute',
  /** Permintaan izin eksplisit (req/res). */
  PERMISSION_REQUEST: 'ruka:permission-request',
  /** Baca pengaturan (req/res; tanpa rahasia). */
  SETTINGS_GET: 'ruka:settings-get',
  /** Patch pengaturan (req/res). */
  SETTINGS_UPDATE: 'ruka:settings-update',
  /** Dorongan status runtime -> renderer (event). */
  RUNTIME_EVENT: 'ruka:runtime-event',
  /** Transkripsi audio lokal/Google via Python brain (req/res). */
  VOICE_TRANSCRIBE: 'ruka:voice-transcribe',
} as const;

/** Tipe amplop — cerminan Envelope Python (protokol v2). */
export interface Envelope<T = any> {
  type: 'request' | 'response' | 'event' | 'error';
  channel: string;
  correlationId: string;
  protocolVersion: number;
  payload: T;
  ts: number;
}

export const PROTOCOL_VERSION = 2;

/** Kanal yang sah utk renderer (putih-list ganda dgn preload). */
export const RENDERER_ALLOWED = new Set<string>([
  IPC.RUNTIME_STATUS,
  IPC.CHAT_SEND,
  IPC.MEMORY_SEARCH,
  IPC.MEMORY_STATS,
  IPC.TOOL_LIST,
  IPC.TOOL_EXECUTE,
  IPC.PERMISSION_REQUEST,
  IPC.SETTINGS_GET,
  IPC.SETTINGS_UPDATE,
  IPC.VOICE_TRANSCRIBE,
]);

/** Validasi kanal — dipanggil handler main utk setiap pesan masuk. */
export function isRendererAllowed(channel: string): boolean {
  return RENDERER_ALLOWED.has(channel);
}
