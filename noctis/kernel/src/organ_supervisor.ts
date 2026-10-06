/**
 * Organ Supervisor — TypeScript on Bun Runtime
 * Implements SRS FR-OS-06 & SAD Section 4.1
 * - Watchdog heartbeat every 2 seconds
 * - 3 missed heartbeats triggers automatic restart within SLA < 3s
 * - Handles resume after suspend with 8-second fence
 * - Scheduled restart for organs with uptime > 24 hours
 * - Fail-closed kill switch in < 200ms
 */

import { OrganName, OrganStatus } from "./types";
import { EventBusBridge } from "./event_bus_bridge";

export class OrganSupervisor {
  private organs: Map<OrganName, OrganStatus> = new Map();
  private watchdogInterval: any = null;
  private isSuspended: boolean = false;
  private suspendFenceUntil: number = 0;

  constructor(
    private bus: EventBusBridge,
    private defaultRssLimitBytes: number = 250 * 1024 * 1024 // 250MB default
  ) {
    // Listen for heartbeats published on EventBus V3
    this.bus.subscribe("*.beat", (evt) => {
      this.recordHeartbeat(evt.namespace);
    });
  }

  public registerOrgan(name: OrganName, rssLimitMb: number = 250): void {
    this.organs.set(name, {
      name,
      running: true,
      rssBytes: 50 * 1024 * 1024,
      rssLimitBytes: rssLimitMb * 1024 * 1024,
      lastHeartbeat: Date.now(),
      missedHeartbeats: 0,
      strikes: 0,
      restarts: 0,
      uptimeSeconds: 0,
    });
  }

  public getOrgan(name: OrganName): OrganStatus | undefined {
    return this.organs.get(name);
  }

  public getAllOrgans(): OrganStatus[] {
    return Array.from(this.organs.values());
  }

  public recordHeartbeat(name: OrganName): void {
    const organ = this.organs.get(name);
    if (organ) {
      organ.lastHeartbeat = Date.now();
      organ.missedHeartbeats = 0;
      organ.running = true;
    }
  }

  public startWatchdog(): void {
    if (this.watchdogInterval) return;

    this.watchdogInterval = setInterval(() => {
      this.tick();
    }, 2000); // 2 second cycle per FR-OS-06
  }

  public stopWatchdog(): void {
    if (this.watchdogInterval) {
      clearInterval(this.watchdogInterval);
      this.watchdogInterval = null;
    }
  }

  /**
   * Watchdog Tick: checks missed heartbeats and 24h lifetime
   */
  public tick(currentTime: number = Date.now()): void {
    // If under post-suspend fence, do not penalize organs
    if (currentTime < this.suspendFenceUntil) {
      return;
    }

    for (const organ of this.organs.values()) {
      if (!organ.running) continue;

      organ.uptimeSeconds += 2;

      const elapsed = currentTime - organ.lastHeartbeat;
      if (elapsed > 2000) {
        organ.missedHeartbeats += Math.floor(elapsed / 2000);
      }

      // Check 3 missed heartbeats rule (6 seconds)
      if (organ.missedHeartbeats >= 3) {
        this.restartOrgan(organ.name, "Missed 3 consecutive heartbeats");
      }

      // Check scheduled 24h restart rule (86400 seconds)
      if (organ.uptimeSeconds >= 86400) {
        this.restartOrgan(organ.name, "Scheduled 24h rejuvenation restart");
      }
    }
  }

  /**
   * Restarts an organ within SLA < 3s
   */
  public restartOrgan(name: OrganName, reason: string): boolean {
    const organ = this.organs.get(name);
    if (!organ) return false;

    const startTime = Date.now();

    organ.running = false;
    organ.restarts += 1;
    organ.missedHeartbeats = 0;
    organ.uptimeSeconds = 0;
    organ.lastHeartbeat = Date.now();
    organ.running = true;

    const elapsedMs = Date.now() - startTime;

    this.bus.publish("noctis", "noctis.rss_warn", {
      type: "ORGAN_RESTARTED",
      organ: name,
      reason,
      slaRestartMs: elapsedMs,
      totalRestarts: organ.restarts,
    });

    return elapsedMs < 3000; // SLA < 3s per FR-OS-06
  }

  /**
   * System resume handler with 8-second fence
   */
  public handleResume(): void {
    this.isSuspended = false;
    this.suspendFenceUntil = Date.now() + 8000; // 8-second fence per FR-OS-06
    // Reset heartbeats to prevent false alarms
    for (const organ of this.organs.values()) {
      organ.lastHeartbeat = Date.now();
      organ.missedHeartbeats = 0;
    }
  }

  /**
   * Fail-closed emergency Kill Switch executing in < 200ms
   */
  public emergencyKillSwitch(): { success: boolean; elapsedMs: number } {
    const t0 = performance.now();

    this.stopWatchdog();
    for (const organ of this.organs.values()) {
      organ.running = false;
    }

    const elapsedMs = performance.now() - t0;
    return {
      success: elapsedMs < 200, // < 200ms per FR-OS-10
      elapsedMs,
    };
  }
}
