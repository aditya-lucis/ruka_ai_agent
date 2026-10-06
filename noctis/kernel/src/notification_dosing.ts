/**
 * Notification Dosing — TypeScript on Bun Runtime
 * Implements SRS FR-OS-05 & SAD Section 4.1
 * - Normal rate limit: at most 1 notification per 10 minutes (600s)
 * - Quiet hours (22:00 to 07:00): urgent notifications only
 * - Whispers batched into an evening envelope delivered at 18:00
 */

import { NotificationItem } from "./types";
import { EventBusBridge } from "./event_bus_bridge";

export class NotificationDosing {
  private lastDispatchedTime: number = 0;
  private whisperEnvelope: NotificationItem[] = [];
  private readonly rateLimitMs: number = 10 * 60 * 1000; // 10 minutes per FR-OS-05

  constructor(private bus: EventBusBridge) {}

  /**
   * Submit a notification for delivery.
   * Returns whether it was dispatched immediately, deferred, or dropped.
   */
  public submit(
    notification: Omit<NotificationItem, "id" | "createdAt">,
    currentTime: number = Date.now(),
    currentHour: number = new Date(currentTime).getHours()
  ): { status: "dispatched" | "batched_whisper" | "rate_limited" | "quiet_hours_blocked"; item: NotificationItem } {
    const item: NotificationItem = {
      ...notification,
      id: `notif_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      createdAt: currentTime,
    };

    // Rule 1: Whispers are batched for 18:00 envelope
    if (item.whisper && !item.urgent) {
      this.whisperEnvelope.push(item);
      return { status: "batched_whisper", item };
    }

    // Rule 2: Quiet hours (22:00 - 07:00) -> only urgent allowed
    const isQuietHours = currentHour >= 22 || currentHour < 7;
    if (isQuietHours && !item.urgent) {
      return { status: "quiet_hours_blocked", item };
    }

    // Rule 3: Rate limiting (max 1 per 10 min) unless urgent
    const elapsed = currentTime - this.lastDispatchedTime;
    if (!item.urgent && elapsed < this.rateLimitMs) {
      return { status: "rate_limited", item };
    }

    // Dispatch
    item.dispatchedAt = currentTime;
    this.lastDispatchedTime = currentTime;

    this.bus.publish("noctis", "noctis.notify", item);

    return { status: "dispatched", item };
  }

  /**
   * Dispatches the batched 18:00 whisper envelope
   */
  public flushWhisperEnvelope(currentTime: number = Date.now()): NotificationItem | null {
    if (this.whisperEnvelope.length === 0) return null;

    const summary: NotificationItem = {
      id: `envelope_${currentTime}`,
      title: "Amplop Senja Marquess (18:00)",
      message: `Terdapat ${this.whisperEnvelope.length} catatan dan janji temu terkumpul hari ini:\n` +
        this.whisperEnvelope.map((w, idx) => `${idx + 1}. ${w.title}: ${w.message}`).join("\n"),
      urgent: false,
      whisper: false,
      createdAt: currentTime,
      dispatchedAt: currentTime,
    };

    this.whisperEnvelope = [];
    this.bus.publish("noctis", "noctis.notify", summary);
    return summary;
  }

  public getBatchedWhisperCount(): number {
    return this.whisperEnvelope.length;
  }
}
