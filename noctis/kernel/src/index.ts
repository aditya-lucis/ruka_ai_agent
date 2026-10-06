/**
 * PROJECT NOCTIS — Companion Operating System Kernel
 * Main Bun Entrypoint
 * Executed via: bun run src/index.ts
 */

import fs from "node:fs";
import path from "node:path";
import { EventBusBridge } from "./event_bus_bridge";
import { OrganSupervisor } from "./organ_supervisor";
import { ResourceGovernor } from "./resource_governor";
import { LunarClock } from "./lunar_clock";
import { SessionRestore } from "./session_restore";
import { ActionRegistry } from "./action_registry";
import { NotificationDosing } from "./notification_dosing";
import { HotConfig } from "./hot_config";
import { NetworkGuard } from "./network_guard";
import { SentryMode } from "./sentry_mode";
import { BootOrchestrator } from "./boot_orchestrator";

function getKernelEndpointPath(): string {
  const localAppData = process.env.LOCALAPPDATA || (process.env.USERPROFILE ? path.join(process.env.USERPROFILE, "AppData", "Local") : path.join(process.cwd(), ".local"));
  return path.join(localAppData, "ruka", "runtime", "kernel-endpoint.json");
}

export class NoctisKernel {
  public port: number;
  public bus: EventBusBridge;
  public supervisor: OrganSupervisor;
  public governor: ResourceGovernor;
  public clock: LunarClock;
  public session: SessionRestore;
  public actions: ActionRegistry;
  public dosing: NotificationDosing;
  public config: HotConfig;
  public network: NetworkGuard;
  public sentry: SentryMode;
  public boot: BootOrchestrator;

  constructor(port: number = 8766) {
    this.port = port;
    this.bus = new EventBusBridge(port);
    this.supervisor = new OrganSupervisor(this.bus);
    this.governor = new ResourceGovernor(this.supervisor, this.bus);
    this.clock = new LunarClock(this.bus);
    this.session = new SessionRestore();
    this.actions = new ActionRegistry();
    this.dosing = new NotificationDosing(this.bus);
    this.config = new HotConfig(this.bus);
    this.network = new NetworkGuard(this.bus);
    this.sentry = new SentryMode(this.bus);
    this.boot = new BootOrchestrator(this.bus);

    this.registerCanonicalOrgans();
  }

  private registerCanonicalOrgans(): void {
    const organs: Array<{ name: any; limitMb: number }> = [
      { name: "heart", limitMb: 350 },
      { name: "palace", limitMb: 500 },
      { name: "converse", limitMb: 400 },
      { name: "eyes", limitMb: 300 },
      { name: "ear", limitMb: 200 },
      { name: "avatar", limitMb: 250 },
      { name: "hands", limitMb: 200 },
      { name: "brain", limitMb: 450 },
      { name: "forge", limitMb: 300 },
    ];

    for (const o of organs) {
      this.supervisor.registerOrgan(o.name, o.limitMb);
    }
  }

  public async start(): Promise<void> {
    console.log("==================================================");
    console.log("PROJECT NOCTIS — AI Companion Operating System Kernel");
    console.log("Runtime: Bun " + process.versions.bun);
    console.log("Persona: Marquis of Trendamis");
    console.log("==================================================");

    // 1. Start EventBus V3 Bridge WebSocket
    this.bus.startServer();
    console.log(`[Kernel] EventBus V3 Bridge active on ws://127.0.0.1:${this.port}`);

    // Tulis endpoint file agar Electron dapat mendeteksi keberadaan kernel
    try {
      const ep = getKernelEndpointPath();
      fs.mkdirSync(path.dirname(ep), { recursive: true });
      fs.writeFileSync(
        ep,
        JSON.stringify(
          {
            host: "127.0.0.1",
            port: this.port,
            pid: process.pid,
            protocol: "ws",
            version: "3.0.0",
          },
          null,
          2
        )
      );
    } catch (e) {
      console.warn("[Kernel] Gagal menulis endpoint JSON:", e);
    }

    // 2. Start Supervisor & Governor patrols
    this.supervisor.startWatchdog();
    this.governor.startPatrol();
    this.clock.start();

    // 3. Execute 9-step gated boot
    console.log("[Kernel] Executing 9-step gated boot sequence...");
    const bootResult = await this.boot.executeBoot();

    if (bootResult.success) {
      console.log(`[Kernel] Boot SUCCESS in ${bootResult.totalDurationMs.toFixed(2)}ms!`);
      const greeting = this.session.getThreeDoseGreeting("clean");
      console.log(`[Kernel] Greeting: "${greeting}"`);
    } else {
      console.error(`[Kernel] Boot FAILED at Step ${bootResult.failedStep}! Fail-closed engaged.`);
    }
  }

  public stop(): void {
    try {
      const ep = getKernelEndpointPath();
      if (fs.existsSync(ep)) fs.unlinkSync(ep);
    } catch {
      // ignore
    }
    this.supervisor.stopWatchdog();
    this.governor.stopPatrol();
    this.clock.stop();
    this.bus.stopServer();
    console.log("[Kernel] Noctis Kernel shutdown complete.");
  }
}

// Auto-run if executed directly
if (import.meta.main) {
  const kernel = new NoctisKernel();
  process.on("SIGINT", () => {
    kernel.stop();
    process.exit(0);
  });
  process.on("SIGTERM", () => {
    kernel.stop();
    process.exit(0);
  });
  kernel.start().catch((err) => {
    console.error("[Kernel] Fatal startup error:", err);
    process.exit(1);
  });
}

