/**
 * PROJECT NOCTIS — Types & Frozen Contracts
 * Compliant with SAD Section 4.3 & SRS Section 3.1.11
 */

export type OrganName =
  | "heart"
  | "palace"
  | "converse"
  | "eyes"
  | "ear"
  | "avatar"
  | "hands"
  | "brain"
  | "forge"
  | "noctis";

export interface EventEnvelope<T = any> {
  id: string;
  topic: string; // e.g. "heart.beat", "noctis.boot"
  namespace: OrganName;
  timestamp: number;
  producer: string;
  payload: T;
}

export type MoonPhase =
  | "dawn"          // 05:00 - 08:00 (Fajar)
  | "morning"       // 08:00 - 12:00 (Pagi)
  | "afternoon"     // 12:00 - 17:00 (Siang)
  | "twilight"      // 17:00 - 19:00 (Senja)
  | "night"         // 19:00 - 23:00 (Malam)
  | "midnight"      // 23:00 - 03:00 (Tengah Malam)
  | "witching_hour"; // 03:00 - 05:00 (Jam Penyihir)

export interface OrganStatus {
  name: OrganName;
  pid?: number;
  running: boolean;
  rssBytes: number;
  rssLimitBytes: number;
  lastHeartbeat: number;
  missedHeartbeats: number;
  strikes: number;
  restarts: number;
  uptimeSeconds: number;
}

export interface ActionItem {
  id: string;
  title: string;
  shortcut?: string;
  category: "system" | "companion" | "memory" | "code" | "settings";
  riskLevel: "green" | "yellow" | "red";
  handler: () => Promise<any> | any;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  urgent: boolean;
  whisper: boolean;
  createdAt: number;
  dispatchedAt?: number;
}

export interface ConfigSchema {
  version: string;
  companionName: string;
  userTitle: string;
  autonomyLevel: number; // 0 to 4
  quietHours: {
    start: number; // e.g. 22
    end: number;   // e.g. 7
  };
  resourceLimits: Record<string, number>; // Organ -> Max RSS MB
  forgeEnabled: boolean;
  networkGuardStrict: boolean;
}

export interface BootStepResult {
  step: number;
  name: string;
  passed: boolean;
  latencyMs: number;
  details?: string;
}
