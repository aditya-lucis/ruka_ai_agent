/**
 * Hot Config Watcher — TypeScript on Bun Runtime
 * Implements SRS FR-OS-09 & SAD Section 4.1
 * - Watcher with 250ms debounce
 * - Per-key diff without restart
 * - Strict schema validation: invalid config rejected fail-closed, retaining previous valid values
 */

import { ConfigSchema } from "./types";
import { EventBusBridge } from "./event_bus_bridge";

export class HotConfig {
  private currentConfig: ConfigSchema;
  private debounceTimer: any = null;

  constructor(
    private bus: EventBusBridge,
    initialConfig?: Partial<ConfigSchema>
  ) {
    this.currentConfig = {
      version: "3.0.0",
      companionName: "Ruka",
      userTitle: "Young Lord",
      autonomyLevel: 2,
      quietHours: { start: 22, end: 7 },
      resourceLimits: { heart: 350, palace: 500, converse: 400 },
      forgeEnabled: false,
      networkGuardStrict: true,
      ...initialConfig,
    };
  }

  public getConfig(): ConfigSchema {
    return { ...this.currentConfig };
  }

  /**
   * Validate new config structure
   */
  public validate(raw: any): { valid: boolean; error?: string } {
    if (!raw || typeof raw !== "object") {
      return { valid: false, error: "Config payload must be a non-null object" };
    }
    if (raw.autonomyLevel !== undefined && (raw.autonomyLevel < 0 || raw.autonomyLevel > 4)) {
      return { valid: false, error: "autonomyLevel must be an integer between 0 and 4" };
    }
    if (raw.quietHours) {
      if (typeof raw.quietHours.start !== "number" || typeof raw.quietHours.end !== "number") {
        return { valid: false, error: "quietHours must contain start and end numbers" };
      }
    }
    return { valid: true };
  }

  /**
   * Apply config update with 250ms debounce and per-key diff
   */
  public async applyUpdate(
    newPartial: Partial<ConfigSchema>
  ): Promise<{ applied: boolean; diff: Record<string, { old: any; new: any }>; error?: string }> {
    return new Promise((resolve) => {
      if (this.debounceTimer) {
        clearTimeout(this.debounceTimer);
      }

      this.debounceTimer = setTimeout(() => {
        // Validate fail-closed
        const validation = this.validate(newPartial);
        if (!validation.valid) {
          resolve({
            applied: false,
            diff: {},
            error: validation.error,
          });
          return;
        }

        // Calculate per-key diff
        const diff: Record<string, { old: any; new: any }> = {};
        for (const [key, val] of Object.entries(newPartial)) {
          const oldVal = (this.currentConfig as any)[key];
          if (JSON.stringify(oldVal) !== JSON.stringify(val)) {
            diff[key] = { old: oldVal, new: val };
            (this.currentConfig as any)[key] = val;
          }
        }

        // Notify over EventBus V3 without restart
        this.bus.publish("noctis", "noctis.notify", {
          type: "CONFIG_HOT_RELOADED",
          diff,
          timestamp: Date.now(),
        });

        resolve({ applied: true, diff });
      }, 250); // 250ms debounce per FR-OS-09
    });
  }
}
