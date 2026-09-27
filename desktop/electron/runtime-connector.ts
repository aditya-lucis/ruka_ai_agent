/**
 * RUKA — konektor runtime Python. Tubuh menghubungi otak.
 * DOC-VERIFIED: net module (docs resmi Electron, Sept 2026);
 * protokol JSONL loopback cerminan ipc/protocol.py Python.
 *
 * Dua kaidah arsitektur (Part XXIII):
 *   1. ELECTRON MATI bukan OTAK MATI — Python tetap hidup, tray
 *      bawah Windows yang menunjuk restart-nya. Konektor hanya
 *      PENGHUBUNG; hidup-matinya tubuh tak boleh menyeret pikiran.
 *   2. PYTHON MATI bukan TUBUH MATI — jendela tetap ada dan jujur
 *      berkata 'OTAK TERPUTUS' + tombol sambung ulang; reconnect
 *      ber-backoff eksponensial (1s..30s) tanpa spin panas.
 *
 * Handshake versi: hello {protocol_version} -> {ok:true|alasan};
 * versi tak cocok = gagal JELAS (negosiasi Python contract.py).
 */

import * as net from 'node:net';
import * as fs from 'node:fs';
import { IPC, PROTOCOL_VERSION, Envelope } from './ipc-contract';

export type RuntimeState =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'version_mismatch';

export interface ConnectorOptions {
  endpointFile: string;
  onState?: (s: RuntimeState) => void;
  baseRetryMs?: number; // default: 1000
  maxRetryMs?: number;  // default: 30000
}

interface Endpoint {
  host: string;
  port: number;
  token: string;
}

export class RuntimeConnector {
  private socket: net.Socket | null = null;
  private endpoint: Endpoint | null = null;
  private state: RuntimeState = 'disconnected';
  private retry = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private buffer = '';
  private streamHandlers = new Map<string, (env: Envelope) => void>();
  private pendingRequests = new Map<
    string,
    {
      resolve: (env: Envelope) => void;
      reject: (err: Error) => void;
      timer: NodeJS.Timeout;
    }
  >();
  private readonly opts: Required<ConnectorOptions>;

  constructor(opts: ConnectorOptions) {
    this.opts = {
      endpointFile: opts.endpointFile,
      onState: opts.onState ?? (() => undefined),
      baseRetryMs: opts.baseRetryMs ?? 1000,
      maxRetryMs: opts.maxRetryMs ?? 30000,
    };
  }

  /**
   * Baca endpoint file — titik temu yang hidup lebih lama dari
   * kedua proses (Part XVI Python: endpoint discovery).
   */
  private readEndpoint(): Endpoint | null {
    try {
      if (!fs.existsSync(this.opts.endpointFile)) {
        return null;
      }
      const data = JSON.parse(fs.readFileSync(this.opts.endpointFile, 'utf-8'));
      if (
        typeof data.host === 'string' &&
        typeof data.port === 'number' &&
        data.port > 0 &&
        typeof data.token === 'string' &&
        data.token.length >= 16
      ) {
        return data as Endpoint;
      }
      return null;
    } catch {
      return null; // belum ada / belum boot = coba lagi nanti
    }
  }

  private setState(s: RuntimeState): void {
    this.state = s;
    this.opts.onState(s);
  }

  start(): Promise<void> {
    this.setState('connecting');
    return this.connectOnce();
  }

  stop(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.socket?.destroy();
    this.socket = null;
    this.setState('disconnected');
  }

  private connectOnce(): Promise<void> {
    return new Promise((resolve) => {
      const ep = this.readEndpoint();
      if (!ep) {
        this.scheduleReconnect();
        resolve();
        return;
      }
      this.endpoint = ep;
      const sock = net.connect(ep.port, ep.host);
      this.socket = sock;

      sock.on('connect', () => {
        // handshake: hello + versi + token loopback
        const hello = {
          type: 'request',
          channel: 'hello',
          correlationId: `hs-${Date.now()}`,
          protocolVersion: PROTOCOL_VERSION,
          payload: {
            protocol_version: PROTOCOL_VERSION,
            token: ep.token,
          },
          ts: Date.now() / 1000,
        };
        sock.write(JSON.stringify(hello) + '\n');
      });

      sock.on('data', (chunk: Buffer) => {
        this.buffer += chunk.toString('utf-8');
        let nl: number;
        while ((nl = this.buffer.indexOf('\n')) >= 0) {
          const line = this.buffer.slice(0, nl).trim();
          this.buffer = this.buffer.slice(nl + 1);
          if (!line) continue;

          let env: Envelope;
          try {
            env = JSON.parse(line) as Envelope;
          } catch {
            continue; // baris rusak: abaikan, jangan panik
          }

          // Selesaikan request yang berkorelasi
          if (env.correlationId && this.pendingRequests.has(env.correlationId)) {
            const req = this.pendingRequests.get(env.correlationId)!;
            clearTimeout(req.timer);
            this.pendingRequests.delete(env.correlationId);
            if (env.type === 'error') {
              req.reject(new Error((env.payload as any)?.error || 'Kesalahan dari otak Python'));
            } else {
              req.resolve(env);
            }
          }

          if (env.channel === 'hello' || env.type === 'response') {
            this.setState('connected');
            this.retry = 0;
          }
          const handler = this.streamHandlers.get(env.channel);
          if (handler) {
            handler(env);
          }
        }
      });

      sock.on('error', () => {
        // Ditangani oleh close handler
      });

      sock.on('close', () => {
        for (const [, req] of this.pendingRequests.entries()) {
          clearTimeout(req.timer);
          req.reject(new Error('Koneksi terputus dari otak Python'));
        }
        this.pendingRequests.clear();
        if (this.state !== 'disconnected') {
          this.scheduleReconnect();
        }
      });

      resolve();
    });
  }

  /** Backoff eksponensial dengan batas atas 30s — tanpa spin panas. */
  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    this.setState('reconnecting');
    const delay = Math.min(
      this.opts.baseRetryMs * Math.pow(2, this.retry),
      this.opts.maxRetryMs
    );
    this.retry += 1;
    this.reconnectTimer = setTimeout(() => {
      void this.connectOnce();
    }, delay);
  }

  /** Permintaan req/res — correlation UUID-like + timeout berbasis map. */
  request(channel: string, payload: object, timeoutMs = 15000): Promise<Envelope> {
    return new Promise((resolve, reject) => {
      if (!this.socket || this.state !== 'connected') {
        reject(new Error('otak Python belum tersambung'));
        return;
      }
      const correlationId = `c-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
      const env: Envelope = {
        type: 'request',
        channel,
        correlationId,
        protocolVersion: PROTOCOL_VERSION,
        payload,
        ts: Date.now() / 1000,
      };

      const timer = setTimeout(() => {
        this.pendingRequests.delete(correlationId);
        reject(new Error(`timeout ${channel} (${timeoutMs} ms)`));
      }, timeoutMs);

      this.pendingRequests.set(correlationId, { resolve, reject, timer });
      this.socket.write(JSON.stringify(env) + '\n');
    });
  }

  envelope(channel: string): Envelope {
    return {
      type: 'event',
      channel,
      correlationId: 'local',
      protocolVersion: PROTOCOL_VERSION,
      payload: { state: this.state },
      ts: Date.now() / 1000,
    };
  }

  onStream(channel: string, cb: (env: Envelope) => void): void {
    this.streamHandlers.set(channel, cb);
  }

  getState(): RuntimeState {
    return this.state;
  }
}
