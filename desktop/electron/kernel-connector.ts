/**
 * PROJECT NOCTIS — Kernel Connector (Electron -> Bun Kernel)
 * Menghubungkan Tubuh Electron ke EventBus V3 Bridge di Bun Runtime (ws://127.0.0.1:8766).
 * Menerima event bus publik: avatar.pose, avatar.viseme, noctis.boot, noctis.ready, noctis.phase, dll.
 */

import fs from 'node:fs';
import path from 'node:path';

export type KernelState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

export interface KernelEvent {
  id: string;
  topic: string;
  namespace: string;
  timestamp: number;
  producer: string;
  payload: any;
}

export interface KernelConnectorOptions {
  wsUrl?: string; // Default: ws://127.0.0.1:8766
  endpointFile?: string;
  onState?: (state: KernelState) => void;
  onEvent?: (event: KernelEvent) => void;
}

export class KernelConnector {
  private ws: any = null;
  private state: KernelState = 'disconnected';
  private reconnectTimer: NodeJS.Timeout | null = null;
  private wsUrl: string = 'ws://127.0.0.1:8766';
  private readonly options: KernelConnectorOptions;

  constructor(options: KernelConnectorOptions = {}) {
    this.options = options;
    if (options.wsUrl) {
      this.wsUrl = options.wsUrl;
    }
  }

  public getState(): KernelState {
    return this.state;
  }

  public start(): void {
    this.connect();
  }

  public stop(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        // ignore
      }
      this.ws = null;
    }
    this.setState('disconnected');
  }

  private setState(newState: KernelState): void {
    if (this.state !== newState) {
      this.state = newState;
      this.options.onState?.(newState);
    }
  }

  private connect(): void {
    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        // ignore
      }
      this.ws = null;
    }

    // Periksa apakah ada endpoint file kustom
    if (this.options.endpointFile && fs.existsSync(this.options.endpointFile)) {
      try {
        const raw = fs.readFileSync(this.options.endpointFile, 'utf-8');
        const data = JSON.parse(raw);
        if (data.port) {
          this.wsUrl = `ws://${data.host || '127.0.0.1'}:${data.port}`;
        }
      } catch {
        // Abaikan, gunakan wsUrl default
      }
    }

    this.setState(this.state === 'disconnected' ? 'connecting' : 'reconnecting');

    try {
      const WebSocketClass = (globalThis as any).WebSocket;
      if (!WebSocketClass) {
        console.warn('[KERNEL-CONNECTOR] WebSocket global tidak ditemukan di lingkungan ini.');
        this.scheduleReconnect(3000);
        return;
      }

      this.ws = new WebSocketClass(this.wsUrl);

      this.ws.onopen = () => {
        console.log(`[KERNEL-CONNECTOR] Tersambung ke Bun Kernel EventBus V3: ${this.wsUrl}`);
        this.setState('connected');
      };

      this.ws.onmessage = (msgEvent: any) => {
        try {
          const raw = typeof msgEvent.data === 'string' ? msgEvent.data : msgEvent.data.toString();
          const parsed = JSON.parse(raw);
          if (parsed && parsed.topic) {
            this.options.onEvent?.(parsed as KernelEvent);
          }
        } catch (err) {
          console.warn('[KERNEL-CONNECTOR] Gagal mem-parse event WebSocket:', err);
        }
      };

      this.ws.onerror = (_err: any) => {
        // Error socket biasa ditangani di onclose
      };

      this.ws.onclose = () => {
        this.ws = null;
        this.scheduleReconnect(2000);
      };
    } catch (err) {
      this.scheduleReconnect(3000);
    }
  }

  private scheduleReconnect(delayMs: number): void {
    if (this.state === 'connected') {
      this.setState('reconnecting');
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delayMs);
  }

  public publish(producer: string, topic: string, payload: any): boolean {
    if (!this.ws || this.state !== 'connected') {
      return false;
    }
    try {
      const msg = JSON.stringify({
        action: 'publish',
        producer,
        topic,
        payload,
      });
      this.ws.send(msg);
      return true;
    } catch (err) {
      console.warn('[KERNEL-CONNECTOR] Gagal mengirim pesan ke Bun Kernel:', err);
      return false;
    }
  }
}
