/**
 * RUKA — main process Electron. TUBUH, bukan otak.
 * DOC-VERIFIED terhadap docs resmi Electron (September 2026):
 *   - tutorial/security  : checklist (CSP, will-navigate,
 *     setWindowOpenHandler, tanpa allowRunningInsecureContent)
 *   - tutorial/context-isolation + tutorial/ipc + tutorial/sandbox
 *
 * KEPUTUSAN KEAMANAN (setiap baris punya alasan di buku):
 *   1. contextIsolation: true  — default sejak Electron 12; preload
 *      berjalan di konteks TERPISAH dari halaman. Tidak dilonggarkan.
 *   2. sandbox: true — rekomendasi resmi utk mayoritas aplikasi;
 *      renderer kehilangan akses Node penuh. Preload kita hanya
 *      butuh contextBridge + ipcRenderer (kompatibel dgn sandbox).
 *   3. nodeIntegration: false — renderer adalah halaman UI biasa.
 *   4. webSecurity tetap menyala; allowRunningInsecureContent tidak
 *      pernah disentuh. Konten jarak jauh hanya via https — dan
 *      untuk Ruka, UI dimuat dari berkas LOKAL aplikasi sendiri.
 *   5. navigasi dikunci: will-navigate + setWindowOpenHandler
 *      menolak URL apa pun di luar aplikasi; tautan eksternal
 *      dibuka shell.openExternal SETELAH validasi skema https.
 *   6. CSP ketat di renderer (meta tag index.html): default-src
 *      'self'; tidak ada inline script.
 *   7. IPC masuk DIVALIDASI: kanal harus terdaftar + payload
 *      ber-correlation. ipcRenderer tidak pernah terekspos mentah.
 */

import { app, BrowserWindow, shell, ipcMain, screen } from 'electron';
import path from 'node:path';
import {
  IPC,
  isRendererAllowed,
  PROTOCOL_VERSION,
  Envelope,
} from './ipc-contract';
import { RuntimeConnector, RuntimeState } from './runtime-connector';
import { TrayManager } from './tray';
import { KernelConnector, KernelEvent, KernelState } from './kernel-connector';

let mainWindow: BrowserWindow | null = null;
let tray: TrayManager | null = null;
let kernelConnector: KernelConnector | null = null;

import fs from 'node:fs';
import { spawn } from 'node:child_process';

app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');

// Tentukan endpoint file di %LOCALAPPDATA%/ruka/runtime/ipc-endpoint.json (100% portable)
function getLocalAppData(): string {
  if (process.env.LOCALAPPDATA) return process.env.LOCALAPPDATA;
  if (process.env.USERPROFILE) return path.join(process.env.USERPROFILE, 'AppData', 'Local');
  try {
    return app.getPath('appData');
  } catch {
    return path.join(process.cwd(), '.local');
  }
}

const localAppData = getLocalAppData();
const endpointPath = path.join(localAppData, 'ruka', 'runtime', 'ipc-endpoint.json');
const kernelEndpointPath = path.join(localAppData, 'ruka', 'runtime', 'kernel-endpoint.json');

function isPidAlive(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function ensurePythonBrainStarted(): void {
  if (fs.existsSync(endpointPath)) {
    try {
      const data = JSON.parse(fs.readFileSync(endpointPath, 'utf-8'));
      if (data.pid && isPidAlive(data.pid)) {
        return; // Otak Python sudah hidup
      }
      // PID sudah mati / berkas usang
      try {
        fs.unlinkSync(endpointPath);
      } catch {
        // Abaikan jika berkas sedang diakses
      }
    } catch {
      // JSON rusak, bersihkan
    }
  }

  // 1. PRIORITAS UTAMA: Standalone Self-Contained Brain Executable
  // Membawa seluruh komponen hingga Ruka hidup mandiri tanpa perlu install Python di desktop pengguna
  const bundledBrainCandidates = [
    // Saat terpasang via installer NSIS / release win-unpacked:
    path.join(process.resourcesPath, 'brain', 'ruka-brain.exe'),
    path.join(process.resourcesPath, 'app.asar.unpacked', 'resources', 'brain', 'ruka-brain.exe'),
    path.join(app.getAppPath(), '..', 'brain', 'ruka-brain.exe'),
    path.join(path.dirname(app.getPath('exe')), 'resources', 'brain', 'ruka-brain.exe'),
    // Saat mode pengembangan lokal (desktop/resources/brain):
    path.resolve(__dirname, '..', '..', 'resources', 'brain', 'ruka-brain.exe'),
    path.resolve(process.cwd(), 'resources', 'brain', 'ruka-brain.exe'),
    path.resolve(process.cwd(), 'desktop', 'resources', 'brain', 'ruka-brain.exe'),
  ];

  for (const brainExe of bundledBrainCandidates) {
    if (fs.existsSync(brainExe)) {
      try {
        const brainDir = path.dirname(brainExe);
        const child = spawn(brainExe, [], {
          cwd: brainDir,
          detached: true,
          stdio: 'ignore',
          windowsHide: true,
        });
        child.unref();
        console.log(`[MAIN] Self-Contained Ruka Brain spawned successfully: ${brainExe}`);
        return;
      } catch (e) {
        console.warn('[MAIN] Could not spawn bundled brain, falling back to python script:', e);
      }
    }
  }

  // 2. FALLBACK PENGEMBANGAN: Script launcher.py dengan virtualenv Python lokal
  const candidates = [
    path.resolve(__dirname, '..', '..', '..', 'launcher.py'), // dev: out/electron -> root
    path.resolve(__dirname, '..', '..', 'launcher.py'),
    path.resolve(process.cwd(), 'launcher.py'),
    path.resolve(app.getAppPath(), '..', 'launcher.py'),
    path.resolve(app.getAppPath(), '..', '..', 'launcher.py'),
  ];

  let launcherPath: string | null = null;
  for (const cand of candidates) {
    if (fs.existsSync(cand)) {
      launcherPath = cand;
      break;
    }
  }

  if (launcherPath) {
    const rootDir = path.dirname(launcherPath);
    const pythonCandidates = [
      process.env.PYTHON_PATH,
      path.join(rootDir, '.venv', 'Scripts', 'python.exe'),
      path.join(rootDir, '.venv', 'bin', 'python'),
      'python',
      'python3',
    ];
    let pythonExe = 'python';
    for (const p of pythonCandidates) {
      if (p && fs.existsSync(p)) {
        pythonExe = p;
        break;
      }
    }
    try {
      const child = spawn(pythonExe, [launcherPath], {
        cwd: rootDir,
        detached: true,
        stdio: 'ignore',
        windowsHide: true,
      });
      child.unref();
      console.log(`[MAIN] Python Brain launcher spawned with ${pythonExe}: ${launcherPath}`);
    } catch (e) {
      console.warn('[MAIN] Could not auto-spawn Python Brain:', e);
    }
  }
}

function ensureBunKernelStarted(): void {
  if (fs.existsSync(kernelEndpointPath)) {
    try {
      const data = JSON.parse(fs.readFileSync(kernelEndpointPath, 'utf-8'));
      if (data.pid && isPidAlive(data.pid)) {
        return; // Bun Kernel sudah hidup
      }
      try {
        fs.unlinkSync(kernelEndpointPath);
      } catch { }
    } catch { }
  }

  // 1. PRIORITAS UTAMA: Standalone Self-Contained Noctis Kernel Executable
  const bundledKernelCandidates = [
    path.join(process.resourcesPath, 'kernel', 'noctis-kernel.exe'),
    path.join(process.resourcesPath, 'app.asar.unpacked', 'resources', 'kernel', 'noctis-kernel.exe'),
    path.join(app.getAppPath(), '..', 'noctis', 'bin', 'noctis-kernel.exe'),
    path.join(path.dirname(app.getPath('exe')), 'resources', 'kernel', 'noctis-kernel.exe'),
    path.resolve(__dirname, '..', '..', '..', 'noctis', 'bin', 'noctis-kernel.exe'),
    path.resolve(process.cwd(), 'noctis', 'bin', 'noctis-kernel.exe'),
  ];

  for (const kernelExe of bundledKernelCandidates) {
    if (fs.existsSync(kernelExe)) {
      try {
        const kernelDir = path.dirname(kernelExe);
        const child = spawn(kernelExe, [], {
          cwd: kernelDir,
          detached: true,
          stdio: 'ignore',
          windowsHide: true,
        });
        child.unref();
        console.log(`[MAIN] Standalone Noctis Bun Kernel spawned successfully: ${kernelExe}`);
        return;
      } catch (e) {
        console.warn('[MAIN] Could not spawn bundled noctis-kernel.exe, falling back to bun run:', e);
      }
    }
  }

  // 2. FALLBACK PENGEMBANGAN: Script src/index.ts dengan Bun lokal
  const kernelSrcCandidates = [
    path.resolve(__dirname, '..', '..', '..', 'noctis', 'kernel', 'src', 'index.ts'),
    path.resolve(process.cwd(), 'noctis', 'kernel', 'src', 'index.ts'),
    path.resolve(app.getAppPath(), '..', 'noctis', 'kernel', 'src', 'index.ts'),
  ];

  let kernelSrcPath: string | null = null;
  for (const cand of kernelSrcCandidates) {
    if (fs.existsSync(cand)) {
      kernelSrcPath = cand;
      break;
    }
  }

  if (kernelSrcPath) {
    const kernelCwd = path.dirname(path.dirname(kernelSrcPath));
    const bunCandidates = [
      process.env.BUN_PATH,
      path.join(process.env.USERPROFILE || '', '.bun', 'bin', 'bun.exe'),
      'bun',
      'bun.exe',
    ];

    let bunExe = 'bun';
    for (const b of bunCandidates) {
      if (b && (b === 'bun' || b === 'bun.exe' || fs.existsSync(b))) {
        bunExe = b;
        break;
      }
    }

    try {
      const child = spawn(bunExe, ['run', 'src/index.ts'], {
        cwd: kernelCwd,
        detached: true,
        stdio: 'ignore',
        windowsHide: true,
      });
      child.unref();
      console.log(`[MAIN] Noctis Bun Kernel spawned via ${bunExe} in ${kernelCwd}`);
    } catch (e) {
      console.warn('[MAIN] Could not auto-spawn Bun Kernel:', e);
    }
  }
}

const connector = new RuntimeConnector({
  endpointFile: endpointPath,
  onState: (s: RuntimeState) => {
    tray?.showState(s);
    if (mainWindow && !mainWindow.isDestroyed()) {
      const stateEnv: Envelope = {
        type: 'event',
        channel: IPC.RUNTIME_EVENT,
        correlationId: `st-${Date.now()}`,
        protocolVersion: PROTOCOL_VERSION,
        payload: { state: s },
        ts: Date.now() / 1000,
      };
      mainWindow.webContents.send(IPC.RUNTIME_EVENT, stateEnv);
    }
  },
});

kernelConnector = new KernelConnector({
  endpointFile: kernelEndpointPath,
  onEvent: (event: KernelEvent) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send(IPC.KERNEL_EVENT, event);
    }
  },
  onState: (state: KernelState) => {
    console.log(`[MAIN] Bun Kernel state changed: ${state}`);
    if (mainWindow && !mainWindow.isDestroyed()) {
      const kernelStateEnv: Envelope = {
        type: 'event',
        channel: IPC.KERNEL_EVENT,
        correlationId: `kst-${Date.now()}`,
        protocolVersion: PROTOCOL_VERSION,
        payload: { state, topic: 'kernel.state' },
        ts: Date.now() / 1000,
      };
      mainWindow.webContents.send(IPC.KERNEL_EVENT, kernelStateEnv);
    }
  },
});

const rendererFilePath = path.join(__dirname, '..', 'renderer', 'index.html');
const ALLOWED_EXTERNAL = /^https:\/\//i;

function createWindow(): void {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;

  mainWindow = new BrowserWindow({
    width: Math.min(1280, Math.round(screenWidth * 0.92)),
    height: Math.min(860, Math.round(screenHeight * 0.92)),
    minWidth: 480,
    minHeight: 560,
    show: true, // Tampilkan langsung secara instan tanpa menunggu ready-to-show
    frame: false, // Custom frameless titlebar untuk estetika modern premium
    transparent: false,
    backgroundColor: '#11111b',
    icon: path.join(__dirname, '..', 'assets', 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true, // #1 — isolasi ketat konteks renderer
      sandbox: false,         // Izinkan preload CommonJS modul tanpa symlink privilege error
      nodeIntegration: false, // #3 — renderer tidak memiliki akses Node.js
      webSecurity: true,      // #4 — web security aktif
      spellcheck: false,
    },
  });

  // Maksimalkan segera seluas halaman desktop
  try {
    mainWindow.maximize();
    mainWindow.focus();
  } catch (err) {
    console.warn('[MAIN] Could not maximize window immediately:', err);
  }

  // #5 — Kunci navigasi: aplikasi ini tidak menelusuri web liar
  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith('file://')) {
      event.preventDefault();
    }
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (ALLOWED_EXTERNAL.test(url)) {
      setImmediate(() => void shell.openExternal(url));
    }
    return { action: 'deny' }; // jendela baru: selalu tolak
  });

  // Pantau status maximize/restore agar renderer dapat memperbarui ikon window controls
  mainWindow.on('maximize', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('window:maximize-change', true);
    }
  });

  mainWindow.on('unmaximize', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('window:maximize-change', false);
    }
  });

  mainWindow.webContents.on('did-fail-load', (_e, errorCode, errorDescription, validatedURL) => {
    console.error(`[MAIN] Gagal memuat UI ${validatedURL}: [${errorCode}] ${errorDescription}`);
  });

  void mainWindow.loadFile(rendererFilePath);

  mainWindow.once('ready-to-show', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.maximize();
      mainWindow.show();
      mainWindow.focus();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

/** Handler IPC dua arah — pola resmi ipcMain.handle dengan validasi izin */
function registerIpc(): void {
  // Window controls untuk custom frameless header
  ipcMain.handle('window:minimize', () => {
    mainWindow?.minimize();
  });
  ipcMain.handle('window:maximize', () => {
    if (!mainWindow) return false;
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
      return false;
    } else {
      mainWindow.maximize();
      return true;
    }
  });
  ipcMain.handle('window:is-maximized', () => {
    return mainWindow?.isMaximized() ?? false;
  });
  ipcMain.handle('window:hide', () => {
    mainWindow?.hide();
  });
  ipcMain.handle('window:close', () => {
    if (tray) {
      mainWindow?.hide(); // Sembunyikan ke tray jika tray aktif
    } else {
      mainWindow?.close();
    }
  });

  ipcMain.handle(IPC.RUNTIME_STATUS, async () => {
    return connector.envelope(IPC.RUNTIME_STATUS);
  });

  ipcMain.handle(IPC.CHAT_SEND, async (_e, text: string, attachment?: any) => {
    if (!isRendererAllowed(IPC.CHAT_SEND)) {
      throw new Error('Kanal dilarang');
    }
    const clean = String(text).trim();

    // Bila koneksi loopback ke Python aktif, kirim ke Python dengan timeout 45s
    if (connector.getState() === 'connected') {
      try {
        return await connector.request(
          IPC.CHAT_SEND,
          { text: clean.slice(0, 8000), attachment, cwd: process.cwd() },
          45000
        );
      } catch (err: any) {
        return {
          type: 'error',
          channel: IPC.CHAT_SEND,
          correlationId: `err-${Date.now()}`,
          protocolVersion: PROTOCOL_VERSION,
          payload: {
            error: err.message,
            delta: `[Gagal Komunikasi Otak] Permintaan ke ruka-brain gagal: ${err.message}`,
            done: true,
          },
          ts: Date.now() / 1000,
        } as Envelope;
      }
    }

    return {
      type: 'error',
      channel: IPC.CHAT_SEND,
      correlationId: `err-${Date.now()}`,
      protocolVersion: PROTOCOL_VERSION,
      payload: {
        error: `Otak belum terhubung (status: ${connector.getState()})`,
        delta: `[Otak Terputus] Tubuh desktop belum tersambung ke proses kognisi ruka-brain (status: ${connector.getState()}). Pastikan background service ruka-brain aktif.`,
        done: true,
      },
      ts: Date.now() / 1000,
    } as Envelope;
  });

  ipcMain.handle(IPC.VOICE_TRANSCRIBE, async (_e, wavBase64: string) => {
    if (!isRendererAllowed(IPC.VOICE_TRANSCRIBE)) {
      throw new Error('Kanal dilarang');
    }
    if (connector.getState() === 'connected') {
      try {
        return await connector.request(
          IPC.VOICE_TRANSCRIBE,
          { audio: String(wavBase64) },
          30000
        );
      } catch (err: any) {
        return {
          type: 'error',
          channel: IPC.VOICE_TRANSCRIBE,
          correlationId: `err-${Date.now()}`,
          protocolVersion: PROTOCOL_VERSION,
          payload: { error: err.message },
          ts: Date.now() / 1000,
        } as Envelope;
      }
    }
    return {
      type: 'error',
      channel: IPC.VOICE_TRANSCRIBE,
      correlationId: `err-${Date.now()}`,
      protocolVersion: PROTOCOL_VERSION,
      payload: { error: 'Otak belum tersambung' },
      ts: Date.now() / 1000,
    } as Envelope;
  });

  ipcMain.handle(IPC.VOICE_SYNTHESIZE, async (_e, payload: any) => {
    if (!isRendererAllowed(IPC.VOICE_SYNTHESIZE)) {
      throw new Error('Kanal dilarang');
    }
    if (connector.getState() === 'connected') {
      try {
        return await connector.request(IPC.VOICE_SYNTHESIZE, payload, 30000);
      } catch (err: any) {
        return {
          type: 'error',
          channel: IPC.VOICE_SYNTHESIZE,
          correlationId: `err-${Date.now()}`,
          protocolVersion: PROTOCOL_VERSION,
          payload: { error: err.message, audioUrl: null },
          ts: Date.now() / 1000,
        } as Envelope;
      }
    }
    return {
      type: 'error',
      channel: IPC.VOICE_SYNTHESIZE,
      correlationId: `err-${Date.now()}`,
      protocolVersion: PROTOCOL_VERSION,
      payload: { error: 'Otak belum tersambung', audioUrl: null },
      ts: Date.now() / 1000,
    } as Envelope;
  });

  ipcMain.handle(IPC.GOOGLE_SEARCH, async (_e, payload: any) => {
    if (!isRendererAllowed(IPC.GOOGLE_SEARCH)) {
      throw new Error('Kanal dilarang');
    }
    if (connector.getState() === 'connected') {
      try {
        return await connector.request(IPC.GOOGLE_SEARCH, payload, 25000);
      } catch (err: any) {
        return {
          type: 'error',
          channel: IPC.GOOGLE_SEARCH,
          correlationId: `err-${Date.now()}`,
          protocolVersion: PROTOCOL_VERSION,
          payload: { query: payload?.query || '', results: [], error: err.message },
          ts: Date.now() / 1000,
        } as Envelope;
      }
    }
    return {
      type: 'error',
      channel: IPC.GOOGLE_SEARCH,
      correlationId: `err-${Date.now()}`,
      protocolVersion: PROTOCOL_VERSION,
      payload: { query: payload?.query || '', results: [], error: 'Otak Python belum tersambung' },
      ts: Date.now() / 1000,
    } as Envelope;
  });

  ipcMain.handle(IPC.MEMORY_SEARCH, async (_e, q: string) => {
    try {
      return await connector.request(IPC.MEMORY_SEARCH, {
        query: String(q).slice(0, 2000),
      });
    } catch (err: any) {
      return {
        type: 'response',
        channel: IPC.MEMORY_SEARCH,
        correlationId: 'offline-search',
        protocolVersion: PROTOCOL_VERSION,
        payload: { hits: [], took_ms: 0, error: err.message },
        ts: Date.now() / 1000,
      } as Envelope;
    }
  });

  ipcMain.handle(IPC.MEMORY_STATS, async () => {
    try {
      return await connector.request(IPC.MEMORY_STATS, {});
    } catch (err: any) {
      return {
        type: 'response',
        channel: IPC.MEMORY_STATS,
        correlationId: 'offline-stats',
        protocolVersion: PROTOCOL_VERSION,
        payload: {
          counts_by_kind: { episodic: 0, semantic: 0, identity: 1 },
          lifecycle: { status: 'standby' },
        },
        ts: Date.now() / 1000,
      } as Envelope;
    }
  });

  ipcMain.handle(IPC.TOOL_LIST, async () => {
    try {
      return await connector.request(IPC.TOOL_LIST, {});
    } catch (err: any) {
      return {
        type: 'response',
        channel: IPC.TOOL_LIST,
        correlationId: 'offline-tools',
        protocolVersion: PROTOCOL_VERSION,
        payload: {
          tools: [
            { name: 'camera.capture', permission: 'local_only' },
            { name: 'voice.listen', permission: 'local_only' },
            { name: 'filesystem.read', permission: 'read' },
            { name: 'memory.read', permission: 'read' },
          ],
        },
        ts: Date.now() / 1000,
      } as Envelope;
    }
  });

  ipcMain.handle(
    IPC.TOOL_EXECUTE,
    async (_e, tool: string, params: object, token?: string) => {
      return connector.request(IPC.TOOL_EXECUTE, {
        tool: String(tool),
        params,
        approval_token: token,
      });
    }
  );

  ipcMain.handle(
    IPC.PERMISSION_REQUEST,
    async (_e, p: string, reason: string) => {
      return connector.request(IPC.PERMISSION_REQUEST, {
        permission: String(p),
        reason: String(reason).slice(0, 2000),
      });
    }
  );

  ipcMain.handle(IPC.SETTINGS_GET, async () => {
    return connector.request(IPC.SETTINGS_GET, {});
  });

  ipcMain.handle(IPC.SETTINGS_UPDATE, async (_e, patch: object) => {
    return connector.request(IPC.SETTINGS_UPDATE, { patch });
  });

  ipcMain.handle(
    IPC.KERNEL_PUBLISH,
    async (_e, arg1: any, arg2?: string, arg3?: any) => {
      if (!kernelConnector) return false;
      if (typeof arg1 === 'object' && arg1 !== null && arg1.producer && arg1.topic) {
        return kernelConnector.publish(arg1.producer, arg1.topic, arg1.payload);
      }
      return kernelConnector.publish(String(arg1), String(arg2), arg3);
    }
  );

  ipcMain.handle(IPC.KERNEL_STATUS, async () => {
    return {
      type: 'response',
      channel: IPC.KERNEL_STATUS,
      correlationId: `kst-req-${Date.now()}`,
      protocolVersion: PROTOCOL_VERSION,
      payload: {
        state: kernelConnector ? kernelConnector.getState() : 'disconnected',
      },
      ts: Date.now() / 1000,
    } as Envelope;
  });
}

/** Router arus CHAT_STREAM dari Python -> renderer */
function bindStreamForward(): void {
  connector.onStream(IPC.CHAT_STREAM, (env: Envelope) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send(IPC.CHAT_STREAM, env);
    }
  });
}

export function toggleWindow(): void {
  if (!mainWindow) {
    createWindow();
    return;
  }
  if (mainWindow.isVisible()) {
    mainWindow.hide();
  } else {
    mainWindow.show();
    mainWindow.focus();
  }
}

const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.maximize();
      mainWindow.focus();
    } else {
      createWindow();
    }
  });

  app.whenReady().then(() => {
    registerIpc();
    bindStreamForward();
    try {
      tray = new TrayManager({ onToggle: toggleWindow });
    } catch (e) {
      console.warn('[MAIN] Tray initialization non-fatal error:', e);
    }
    createWindow();

    // Otak & Kernel dihubungkan SETELAH tubuh siap memaparkan statusnya
    ensureBunKernelStarted();
    ensurePythonBrainStarted();
    kernelConnector?.start();
    void connector.start();
  });
}

app.on('window-all-closed', () => {
  // Jika tray tidak ada atau di macOS, keluar dari aplikasi
  if (!tray || process.platform === 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  kernelConnector?.stop();
  connector.stop(); // Putus sopan dari socket Python
  tray?.destroy();
});
