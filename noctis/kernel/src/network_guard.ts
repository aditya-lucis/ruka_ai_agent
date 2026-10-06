/**
 * Network Guard — TypeScript on Bun Runtime
 * Implements SRS FR-OS-12 & SAD Section 4.1
 * - Enforces zero unauthorized outbound network sockets
 * - Whitelists only official signed update endpoint
 * - Emits 'noctis.net_alert' upon unauthorized connection attempt
 */

import { EventBusBridge } from "./event_bus_bridge";

export class NetworkGuard {
  private allowedEndpoints: Set<string> = new Set([
    "updates.trendamis.org",
    "127.0.0.1",
    "localhost",
  ]);

  constructor(private bus: EventBusBridge) {}

  public allowEndpoint(host: string): void {
    this.allowedEndpoints.add(host);
  }

  /**
   * Evaluates an outbound connection request
   */
  public evaluateOutbound(host: string, port: number): { allowed: boolean; reason: string } {
    const isAllowed = this.allowedEndpoints.has(host) || host.endsWith(".trendamis.org");

    if (!isAllowed) {
      this.bus.publish("noctis", "noctis.notify", {
        type: "NET_ALERT_BLOCKED",
        targetHost: host,
        targetPort: port,
        reason: "Unauthorized outbound socket blocked by NetworkGuard",
        timestamp: Date.now(),
      });

      return {
        allowed: false,
        reason: `Outbound connection to '${host}:${port}' blocked by NetworkGuard (FR-OS-12 zero-outbound rule).`,
      };
    }

    return { allowed: true, reason: "Allowed official endpoint or local loopback" };
  }
}
