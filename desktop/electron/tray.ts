/**
 * RUKA — tray. Kehadiran kecil di sudut layar yang jujur.
 * DOC-VERIFIED: Tray + Menu (docs resmi Electron, Sept 2026);
 * klik = toggle (Windows: boundingRect default), klik-kanan =
 * menu konteks; icon status dibangun dari nativeImage.
 *
 * Tray adalah BAGIAN TUBUH yang PALING sering dilihat Bos —
 * statusnya harus jujur: hijau siap, kuning degraded, merah
 * terputus. Jangan pernah hijau saat Python mati; tray berbohong
 * = kepercayaan pertama yang jatuh.
 */

import { Tray, Menu, nativeImage, app } from 'electron';
import path from 'node:path';
import fs from 'node:fs';
import { RuntimeState } from './runtime-connector';

interface TrayOptions {
  onToggle: () => void;
}

const STATE_LABEL: Record<RuntimeState, string> = {
  connected: 'Ruka siap (Aktif)',
  connecting: 'Menyambung ke pikiran…',
  reconnecting: 'Pikiran terputus — menyambung ulang',
  disconnected: 'Ruka offline',
  version_mismatch: 'Versi tubuh/otak tak cocok',
};

// SVG data URI untuk icon status 16x16 jika berkas PNG belum ada di disk
function generateSvgIcon(color: string): Electron.NativeImage {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
    <circle cx="8" cy="8" r="7" fill="#181825" stroke="${color}" stroke-width="1.5" />
    <circle cx="8" cy="8" r="4" fill="${color}" />
  </svg>`;
  return nativeImage.createFromBuffer(Buffer.from(svg));
}

export class TrayManager {
  private tray: Tray | null = null;
  private state: RuntimeState = 'disconnected';

  constructor(private opts: TrayOptions) {
    this.tray = new Tray(this.getIcon('disconnected'));
    this.tray.setToolTip('RUKA — The Persistent Mind');
    this.rebuild();

    // Klik kiri = toggle jendela (Windows). Klik kanan = menu konteks
    this.tray.on('click', () => this.opts.onToggle());
  }

  private getIcon(s: RuntimeState): Electron.NativeImage {
    const fileMap: Record<RuntimeState, string> = {
      connected: 'tray-ready.png',
      connecting: 'tray-degraded.png',
      reconnecting: 'tray-degraded.png',
      disconnected: 'tray-offline.png',
      version_mismatch: 'tray-offline.png',
    };
    const colorMap: Record<RuntimeState, string> = {
      connected: '#a6e3a1',       // Green
      connecting: '#f9e2af',      // Yellow
      reconnecting: '#fab387',    // Orange
      disconnected: '#f38ba8',    // Red
      version_mismatch: '#f38ba8',// Red
    };

    const assetPath = path.join(__dirname, '..', 'assets', fileMap[s]);
    if (fs.existsSync(assetPath)) {
      return nativeImage.createFromPath(assetPath);
    }
    return generateSvgIcon(colorMap[s]);
  }

  showState(s: RuntimeState): void {
    this.state = s;
    if (!this.tray) return;
    this.tray.setImage(this.getIcon(s));
    this.tray.setToolTip(`RUKA — ${STATE_LABEL[s]}`);
    this.rebuild();
  }

  private rebuild(): void {
    if (!this.tray) return;
    const label = STATE_LABEL[this.state];
    this.tray.setContextMenu(
      Menu.buildFromTemplate([
        { label: `Status: ${label}`, enabled: false },
        { type: 'separator' },
        {
          label: 'Tampilkan / Sembunyikan Jendela',
          click: () => this.opts.onToggle(),
        },
        {
          label: 'Diagnostik Runtime',
          click: () => this.opts.onToggle(),
        },
        { type: 'separator' },
        {
          label: 'Keluar dari RUKA',
          click: () => app.quit(),
        },
      ])
    );
  }

  destroy(): void {
    this.tray?.destroy();
    this.tray = null;
  }
}
