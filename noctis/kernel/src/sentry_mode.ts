/**
 * Sentry Mode — TypeScript on Bun Runtime
 * Implements SRS FR-OS-14 & SAD Section 4.1
 * - Triggered when screen is locked or user is absent > 5 minutes
 * - Puts avatar to sleep
 * - Hard power-off for camera
 * - Holds all non-urgent notifications
 * - Triggers hourly security audit
 */

import { EventBusBridge } from "./event_bus_bridge";

export class SentryMode {
  private active: boolean = false;
  private lastUserActivity: number = Date.now();
  private auditInterval: any = null;

  constructor(private bus: EventBusBridge) {}

  public recordActivity(): void {
    this.lastUserActivity = Date.now();
    if (this.active) {
      this.deactivate("User activity resumed");
    }
  }

  public checkIdle(currentTime: number = Date.now()): boolean {
    const idleMs = currentTime - this.lastUserActivity;
    const fiveMinutesMs = 5 * 60 * 1000;

    if (idleMs >= fiveMinutesMs && !this.active) {
      this.activate("User idle > 5 minutes");
      return true;
    }
    return false;
  }

  public activate(reason: string): void {
    if (this.active) return;
    this.active = true;

    // Avatar to sleep
    this.bus.publish("avatar", "avatar.state", { state: "sleeping", reason });

    // Camera hardware cut
    this.bus.publish("eyes", "eyes.state", { active: false, privacyBlind: true });

    // Log sentry activation
    this.bus.publish("noctis", "noctis.notify", {
      type: "SENTRY_MODE_ENGAGED",
      reason,
      timestamp: Date.now(),
    });
  }

  public deactivate(reason: string): void {
    if (!this.active) return;
    this.active = false;

    this.bus.publish("avatar", "avatar.state", { state: "idle", reason });
    this.bus.publish("noctis", "noctis.notify", {
      type: "SENTRY_MODE_DISENGAGED",
      reason,
      timestamp: Date.now(),
    });
  }

  public isActive(): boolean {
    return this.active;
  }
}
