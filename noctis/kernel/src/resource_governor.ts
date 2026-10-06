/**
 * Resource Governor — TypeScript on Bun Runtime
 * Implements SRS FR-OS-08 & SAD Section 4.1
 * - RAM/RSS budget tracking per organ
 * - Patrol every 60 seconds
 * - 90% budget redline threshold
 * - 3 consecutive violations triggers kill & restart
 * - Automatic GPU LOD downgrade if graphics memory over budget
 */

import { OrganName } from "./types";
import { OrganSupervisor } from "./organ_supervisor";
import { EventBusBridge } from "./event_bus_bridge";

export class ResourceGovernor {
  private patrolInterval: any = null;
  private currentLod: number = 0; // 0 = Full, 1 = Med, 2 = Low, 3 = Minimal
  private gpuMemoryUsageMb: number = 200;
  private readonly gpuBudgetMb: number = 512;

  constructor(
    private supervisor: OrganSupervisor,
    private bus: EventBusBridge
  ) {}

  public startPatrol(): void {
    if (this.patrolInterval) return;

    this.patrolInterval = setInterval(() => {
      this.patrol();
    }, 60000); // 60s patrol interval per FR-OS-08
  }

  public stopPatrol(): void {
    if (this.patrolInterval) {
      clearInterval(this.patrolInterval);
      this.patrolInterval = null;
    }
  }

  /**
   * Run a single patrol cycle across all organs
   */
  public patrol(): { warned: string[]; killed: string[]; lodDowngraded: boolean } {
    const warned: string[] = [];
    const killed: string[] = [];
    let lodDowngraded = false;

    const organs = this.supervisor.getAllOrgans();

    for (const organ of organs) {
      const redlineBytes = organ.rssLimitBytes * 0.9; // 90% redline

      if (organ.rssBytes >= redlineBytes) {
        organ.strikes += 1;
        warned.push(organ.name);

        this.bus.publish("noctis", "noctis.rss_warn", {
          organ: organ.name,
          rssBytes: organ.rssBytes,
          limitBytes: organ.rssLimitBytes,
          strikes: organ.strikes,
          redlinePct: 90,
        });

        // 3 strikes rule: kill and restart
        if (organ.strikes >= 3) {
          killed.push(organ.name);
          this.bus.publish("noctis", "noctis.rss_warn", {
            type: "KILL_TRIGGERED",
            organ: organ.name,
            reason: "3 consecutive 90% RAM redline violations",
          });

          this.supervisor.restartOrgan(
            organ.name,
            "ResourceGovernor: 3 strikes RAM limit exceeded"
          );
          organ.strikes = 0;
          organ.rssBytes = Math.floor(organ.rssLimitBytes * 0.3); // Reset to base memory
        }
      } else {
        // Recovery: if back under 90%, decay strikes
        if (organ.strikes > 0) {
          organ.strikes -= 1;
        }
      }
    }

    // Check GPU memory budget for avatar LOD degradation
    if (this.gpuMemoryUsageMb > this.gpuBudgetMb && this.currentLod < 3) {
      this.currentLod += 1;
      lodDowngraded = true;
      this.bus.publish("avatar", "avatar.lod", {
        newLod: this.currentLod,
        reason: "GPU memory exceeded budget, downgrading LOD",
      });
    }

    return { warned, killed, lodDowngraded };
  }

  public reportMemory(organName: OrganName, bytes: number): void {
    const organ = this.supervisor.getOrgan(organName);
    if (organ) {
      organ.rssBytes = bytes;
    }
  }

  public reportGpuUsage(mb: number): void {
    this.gpuMemoryUsageMb = mb;
  }

  public getCurrentLod(): number {
    return this.currentLod;
  }
}
