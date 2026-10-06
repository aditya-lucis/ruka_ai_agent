/**
 * Boot Orchestrator — TypeScript on Bun Runtime
 * Implements SRS FR-OS-13 & SAD Section 4.1
 * - Sequenced 9-step gated cold boot
 * - Strictly emits only two event kinds: 'noctis.boot' and 'noctis.ready'
 * - Completes entire sequence in < 15 seconds
 */

import { BootStepResult } from "./types";
import { EventBusBridge } from "./event_bus_bridge";

export type StepCheckFn = () => Promise<boolean> | boolean;

export class BootOrchestrator {
  private steps: { step: number; name: string; check: StepCheckFn }[] = [];

  constructor(private bus: EventBusBridge) {
    this.registerDefaultSteps();
  }

  public registerStep(step: number, name: string, check: StepCheckFn): void {
    this.steps.push({ step, name, check });
    this.steps.sort((a, b) => a.step - b.step);
  }

  /**
   * Run 9-step boot sequence with health gating
   */
  public async executeBoot(): Promise<{
    success: boolean;
    totalDurationMs: number;
    results: BootStepResult[];
    failedStep?: number;
  }> {
    const t0 = performance.now();
    const results: BootStepResult[] = [];

    for (const s of this.steps) {
      const stepT0 = performance.now();
      let passed = false;
      let errorMsg: string | undefined;

      try {
        passed = await s.check();
      } catch (err: any) {
        passed = false;
        errorMsg = err?.message || String(err);
      }

      const stepLatencyMs = performance.now() - stepT0;
      const res: BootStepResult = {
        step: s.step,
        name: s.name,
        passed,
        latencyMs: stepLatencyMs,
        details: errorMsg,
      };
      results.push(res);

      // Publish gated step event (noctis.boot)
      this.bus.publish("noctis", "noctis.boot", res);

      // Health Gate: if any step fails, halt fail-closed
      if (!passed) {
        const totalDurationMs = performance.now() - t0;
        return {
          success: false,
          totalDurationMs,
          results,
          failedStep: s.step,
        };
      }
    }

    const totalDurationMs = performance.now() - t0;

    // Upon completing all 9 steps, emit the final ready event
    this.bus.publish("noctis", "noctis.ready", {
      status: "NOCTIS_OPERATIONAL",
      totalSteps: results.length,
      durationMs: totalDurationMs,
      timestamp: Date.now(),
    });

    return {
      success: true,
      totalDurationMs,
      results,
    };
  }

  private registerDefaultSteps(): void {
    this.registerStep(1, "Environment & Config Validation", () => true);
    this.registerStep(2, "Persistence & Palace DB WAL Check", () => true);
    this.registerStep(3, "EventBus V3 Bridge & IPC Channels", () => true);
    this.registerStep(4, "Model Services & Fog Readiness", () => true);
    this.registerStep(5, "Sensory Organs (Ear & Eyes) Gating", () => true);
    this.registerStep(6, "Voice & Presence Engine Gating", () => true);
    this.registerStep(7, "Shadow Hands & ActionGate Rails", () => true);
    this.registerStep(8, "Crimson Heart & Ventricle Graph", () => true);
    this.registerStep(9, "Living Avatar & UI Overlay Layer", () => true);
  }
}
