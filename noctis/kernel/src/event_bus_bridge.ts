/**
 * EventBus V3 Bridge — TypeScript on Bun Runtime
 * Implements SAD Section 4.3 (Event Contract) & Table 1 (Architectural Patterns)
 * - Strict per-organ namespace enforcement
 * - Drop-oldest ring buffer (max 64 events drain per frame)
 * - WebSocket server for Electron overlay and Python sidecar interconnect
 */

import { EventEnvelope, OrganName } from "./types";

export type EventCallback = (event: EventEnvelope) => void;

export class EventBusBridge {
  private subscribers: Map<string, Set<EventCallback>> = new Map();
  private ringBuffer: EventEnvelope[] = [];
  private readonly maxBufferSize: number = 256;
  private readonly maxDrainPerTick: number = 64;
  private server: any = null;
  private connectedSockets: Set<any> = new Set();

  constructor(private port: number = 8766) {}

  /**
   * Subscribe to an event topic pattern (e.g. "heart.*", "noctis.boot", "*")
   */
  public subscribe(pattern: string, callback: EventCallback): () => void {
    if (!this.subscribers.has(pattern)) {
      this.subscribers.set(pattern, new Set());
    }
    this.subscribers.get(pattern)!.add(callback);

    // Unsubscribe handle
    return () => {
      const set = this.subscribers.get(pattern);
      if (set) {
        set.delete(callback);
        if (set.size === 0) this.subscribers.delete(pattern);
      }
    };
  }

  /**
   * Publish an event. Enforces namespace matching producer.
   * If namespace does not match topic prefix, raises runtime permission error.
   */
  public publish<T = any>(
    producer: OrganName,
    topic: string,
    payload: T
  ): EventEnvelope<T> {
    const topicNamespace = topic.split(".")[0] as OrganName;
    if (topicNamespace !== producer && producer !== "noctis") {
      throw new Error(
        `[EventBusV3] Namespace violation! Producer '${producer}' cannot publish to '${topic}'`
      );
    }

    const envelope: EventEnvelope<T> = {
      id: `evt_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
      topic,
      namespace: topicNamespace,
      timestamp: Date.now(),
      producer,
      payload,
    };

    // Push into ring buffer (drop-oldest policy)
    if (this.ringBuffer.length >= this.maxBufferSize) {
      this.ringBuffer.shift(); // Drop oldest
    }
    this.ringBuffer.push(envelope);

    // Broadcast immediately to in-memory listeners
    this.dispatchToSubscribers(envelope);

    // Broadcast over WebSocket if active
    this.broadcastWs(envelope);

    return envelope;
  }

  /**
   * Drain up to 64 events from the ring buffer
   */
  public drain(max: number = this.maxDrainPerTick): EventEnvelope[] {
    const count = Math.min(max, this.ringBuffer.length);
    return this.ringBuffer.splice(0, count);
  }

  public getBufferSize(): number {
    return this.ringBuffer.length;
  }

  private dispatchToSubscribers(envelope: EventEnvelope): void {
    for (const [pattern, cbs] of this.subscribers.entries()) {
      if (this.matchesPattern(pattern, envelope.topic)) {
        for (const cb of cbs) {
          try {
            cb(envelope);
          } catch (err) {
            console.error(`[EventBusV3] Error in subscriber for ${pattern}:`, err);
          }
        }
      }
    }
  }

  private matchesPattern(pattern: string, topic: string): boolean {
    if (pattern === "*" || pattern === topic) return true;
    if (pattern.endsWith(".*")) {
      const prefix = pattern.slice(0, -2);
      return topic.startsWith(prefix + ".");
    }
    return false;
  }

  /**
   * Start Bun WebSocket Bridge server for external processes
   */
  public startServer(): void {
    if (this.server) return;

    const self = this;
    this.server = Bun.serve({
      hostname: "127.0.0.1",
      port: this.port,
      fetch(req, server) {
        // Zero-Trust: Tolak Cross-Site WebSocket Hijacking dari browser eksternal
        const origin = req.headers.get("origin");
        if (
          origin &&
          !origin.includes("localhost") &&
          !origin.includes("127.0.0.1") &&
          !origin.startsWith("file://") &&
          !origin.startsWith("vscode-webview://")
        ) {
          return new Response("Forbidden", { status: 403 });
        }

        if (server.upgrade(req)) {
          return;
        }
        return new Response("PROJECT NOCTIS — EventBus V3 Bridge", { status: 200 });
      },
      websocket: {
        open(ws) {
          self.connectedSockets.add(ws);
        },
        message(ws, message) {
          try {
            const raw = typeof message === "string" ? message : new TextDecoder().decode(message);
            const data = JSON.parse(raw);
            if (data.action === "publish" && data.producer && data.topic) {
              self.publish(data.producer, data.topic, data.payload);
            }
          } catch (err) {
            ws.send(JSON.stringify({ error: "Invalid JSON event format" }));
          }
        },
        close(ws) {
          self.connectedSockets.delete(ws);
        },
      },
    });
  }

  private broadcastWs(envelope: EventEnvelope): void {
    if (this.connectedSockets.size === 0) return;
    const msg = JSON.stringify(envelope);
    for (const ws of this.connectedSockets) {
      try {
        ws.send(msg);
      } catch {
        // ignore closed socket
      }
    }
  }

  public stopServer(): void {
    if (this.server) {
      this.server.stop(true);
      this.server = null;
    }
    this.connectedSockets.clear();
  }
}
