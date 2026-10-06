/**
 * Lunar Clock — TypeScript on Bun Runtime
 * Implements SRS FR-OS-07 & SAD Section 4.1
 * - 7 diurnal moon phases
 * - Governs mood floor, level ceiling, and night speech permission
 * - Emits 'noctis.phase' upon transition
 */

import { MoonPhase } from "./types";
import { EventBusBridge } from "./event_bus_bridge";

export interface PhaseProperties {
  phase: MoonPhase;
  moodFloor: number;      // Minimum allowed mood (0.0 - 1.0)
  levelCeiling: number;   // Maximum autonomy intensity (0 - 4)
  allowVoice: boolean;    // Whether normal voice playback is allowed
  description: string;
}

export class LunarClock {
  private currentPhase: MoonPhase = "morning";
  private checkInterval: any = null;

  constructor(private bus: EventBusBridge) {
    this.updatePhase(new Date());
  }

  public getPhaseForHour(hour: number): MoonPhase {
    if (hour >= 5 && hour < 8) return "dawn";
    if (hour >= 8 && hour < 12) return "morning";
    if (hour >= 12 && hour < 17) return "afternoon";
    if (hour >= 17 && hour < 19) return "twilight";
    if (hour >= 19 && hour < 23) return "night";
    if (hour >= 23 || hour < 3) return "midnight";
    return "witching_hour"; // 03:00 - 05:00
  }

  public getProperties(phase: MoonPhase = this.currentPhase): PhaseProperties {
    switch (phase) {
      case "dawn":
        return {
          phase: "dawn",
          moodFloor: 0.5,
          levelCeiling: 3,
          allowVoice: true,
          description: "Fajar menyingsing, Marquess terbangun perlahan.",
        };
      case "morning":
        return {
          phase: "morning",
          moodFloor: 0.6,
          levelCeiling: 4,
          allowVoice: true,
          description: "Pagi penuh energi dan ketajaman intelektual.",
        };
      case "afternoon":
        return {
          phase: "afternoon",
          moodFloor: 0.5,
          levelCeiling: 4,
          allowVoice: true,
          description: "Siang hari stabil dalam produktivitas.",
        };
      case "twilight":
        return {
          phase: "twilight",
          moodFloor: 0.4,
          levelCeiling: 3,
          allowVoice: true,
          description: "Senja tiba, saatnya merangkum janji dan berbisik.",
        };
      case "night":
        return {
          phase: "night",
          moodFloor: 0.3,
          levelCeiling: 2,
          allowVoice: true,
          description: "Malam tenang, volume suara melembut.",
        };
      case "midnight":
        return {
          phase: "midnight",
          moodFloor: 0.2,
          levelCeiling: 1,
          allowVoice: false, // Quiet hours: whispers only
          description: "Tengah malam sunyi, mode hening diutamakan.",
        };
      case "witching_hour":
        return {
          phase: "witching_hour",
          moodFloor: 0.1,
          levelCeiling: 1,
          allowVoice: false, // Absolute quiet unless urgent
          description: "Jam penyihir, istana memori berkonsolidasi.",
        };
    }
  }

  public updatePhase(date: Date = new Date()): boolean {
    const hour = date.getHours();
    const newPhase = this.getPhaseForHour(hour);

    if (newPhase !== this.currentPhase) {
      const oldPhase = this.currentPhase;
      this.currentPhase = newPhase;
      const props = this.getProperties(newPhase);

      this.bus.publish("noctis", "noctis.phase", {
        from: oldPhase,
        to: newPhase,
        properties: props,
        timestamp: date.getTime(),
      });
      return true;
    }
    return false;
  }

  public getCurrentPhase(): MoonPhase {
    return this.currentPhase;
  }

  public start(): void {
    if (this.checkInterval) return;
    this.checkInterval = setInterval(() => {
      this.updatePhase();
    }, 60000); // Check every minute
  }

  public stop(): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
  }
}
