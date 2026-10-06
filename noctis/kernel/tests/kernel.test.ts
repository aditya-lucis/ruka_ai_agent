/**
 * PROJECT NOCTIS — Bun Kernel Test Suite
 * Executed via: bun test
 */

import { describe, expect, it } from "bun:test";
import { EventBusBridge } from "../src/event_bus_bridge";
import { OrganSupervisor } from "../src/organ_supervisor";
import { ResourceGovernor } from "../src/resource_governor";
import { LunarClock } from "../src/lunar_clock";
import { SessionRestore } from "../src/session_restore";
import { ActionRegistry } from "../src/action_registry";
import { NotificationDosing } from "../src/notification_dosing";
import { HotConfig } from "../src/hot_config";
import { NetworkGuard } from "../src/network_guard";
import { SentryMode } from "../src/sentry_mode";
import { BootOrchestrator } from "../src/boot_orchestrator";

describe("PROJECT NOCTIS — Bun Kernel Architecture", () => {
  it("FR-OS-01..03 / EventBus V3 enforces per-organ namespace and drop-oldest ring buffer", () => {
    const bus = new EventBusBridge(9876);
    const events: string[] = [];

    bus.subscribe("heart.*", (evt) => {
      events.push(evt.topic);
    });

    // Valid publish within namespace
    bus.publish("heart", "heart.beat", { pulse: 1 });
    expect(events).toContain("heart.beat");

    // Illegal cross-namespace publish MUST throw runtime permission error
    expect(() => {
      bus.publish("eyes", "heart.beat", { spoof: true });
    }).toThrow("Namespace violation");

    // Ring buffer drain
    const drained = bus.drain(10);
    expect(drained.length).toBeGreaterThan(0);
  });

  it("FR-OS-06 / OrganSupervisor watchdog: 3 missed beats trigger restart SLA < 3s, kill switch < 200ms", () => {
    const bus = new EventBusBridge(9877);
    const supervisor = new OrganSupervisor(bus);

    supervisor.registerOrgan("heart", 350);
    const heart = supervisor.getOrgan("heart")!;
    expect(heart.running).toBe(true);

    // Simulate 3 missed beats (elapsed > 6000ms)
    heart.lastHeartbeat = Date.now() - 7000;
    supervisor.tick(Date.now());

    expect(heart.restarts).toBe(1);
    expect(heart.running).toBe(true);

    // Emergency kill switch must be < 200ms
    const killResult = supervisor.emergencyKillSwitch();
    expect(killResult.success).toBe(true);
    expect(killResult.elapsedMs).toBeLessThan(200);
    expect(heart.running).toBe(false);
  });

  it("FR-OS-06 / OrganSupervisor handles post-suspend resume with 8s fence", () => {
    const bus = new EventBusBridge(9878);
    const supervisor = new OrganSupervisor(bus);
    supervisor.registerOrgan("palace", 400);

    const palace = supervisor.getOrgan("palace")!;
    palace.lastHeartbeat = Date.now() - 10000; // Old timestamp before suspend

    // Resume from suspend
    supervisor.handleResume();

    // Tick within fence period
    supervisor.tick(Date.now() + 2000);
    // Should NOT trigger premature restart because fence is active
    expect(palace.restarts).toBe(0);
  });

  it("FR-OS-08 / ResourceGovernor patrols RAM redline (90%) and executes 3-strike restart", () => {
    const bus = new EventBusBridge(9879);
    const supervisor = new OrganSupervisor(bus);
    const governor = new ResourceGovernor(supervisor, bus);

    supervisor.registerOrgan("converse", 100); // 100MB limit
    const converse = supervisor.getOrgan("converse")!;

    // Set usage to 95MB (> 90MB redline)
    governor.reportMemory("converse", 95 * 1024 * 1024);

    // Strike 1
    governor.patrol();
    expect(converse.strikes).toBe(1);

    // Strike 2
    governor.patrol();
    expect(converse.strikes).toBe(2);

    // Strike 3 -> Kill and restart
    const res3 = governor.patrol();
    expect(res3.killed).toContain("converse");
    expect(converse.restarts).toBe(1);
    expect(converse.strikes).toBe(0);
  });

  it("FR-OS-07 / LunarClock enforces 7 diurnal moon phases and quiet hours", () => {
    const bus = new EventBusBridge(9880);
    const clock = new LunarClock(bus);

    expect(clock.getPhaseForHour(6)).toBe("dawn");
    expect(clock.getPhaseForHour(10)).toBe("morning");
    expect(clock.getPhaseForHour(14)).toBe("afternoon");
    expect(clock.getPhaseForHour(18)).toBe("twilight");
    expect(clock.getPhaseForHour(20)).toBe("night");
    expect(clock.getPhaseForHour(0)).toBe("midnight");
    expect(clock.getPhaseForHour(4)).toBe("witching_hour");

    // Midnight props: quiet hours (allowVoice = false)
    const midnightProps = clock.getProperties("midnight");
    expect(midnightProps.allowVoice).toBe(false);

    // Morning props: active voice (allowVoice = true)
    const morningProps = clock.getProperties("morning");
    expect(morningProps.allowVoice).toBe(true);
  });

  it("FR-OS-10 / SessionRestore recovers WAL journal < 15s and returns 3-dose greetings", async () => {
    const restore = new SessionRestore();

    const result = await restore.restore("clean");
    expect(result.restored).toBe(true);
    expect(result.durationMs).toBeLessThan(15000);
    expect(result.greeting).toContain("Young Lord");

    const soft = restore.getThreeDoseGreeting("soft_crash");
    expect(soft).toContain("Sir");

    const hard = restore.getThreeDoseGreeting("hard_crash");
    expect(hard).toContain("My Lord");
  });

  it("FR-OS-04 / ActionRegistry provides single implementation and fuzzy search max 8 results", () => {
    const registry = new ActionRegistry();

    // Verify default actions registered
    expect(registry.getAll().length).toBeGreaterThanOrEqual(8);

    // Fuzzy search for "kill"
    const results = registry.search("kill", 8);
    expect(results.length).toBeGreaterThan(0);
    expect(results.length).toBeLessThanOrEqual(8);
    expect(results[0].id).toBe("noctis.kill_switch");

    // Search empty query returns at most 8
    const top8 = registry.search("", 8);
    expect(top8.length).toBe(8);
  });

  it("FR-OS-05 / NotificationDosing: max 1 per 10m normal, 22-07 quiet hours urgent only, 18:00 whisper envelope", () => {
    const bus = new EventBusBridge(9881);
    const dosing = new NotificationDosing(bus);
    const now = Date.now();

    // 1. First normal notification dispatches at 14:00 (hour 14)
    const r1 = dosing.submit({ title: "Task Complete", message: "Build success", urgent: false, whisper: false }, now, 14);
    expect(r1.status).toBe("dispatched");

    // 2. Second normal notification 2 minutes later is rate-limited (limit 10m)
    const r2 = dosing.submit({ title: "Next Task", message: "Linting", urgent: false, whisper: false }, now + 120000, 14);
    expect(r2.status).toBe("rate_limited");

    // 3. Urgent notification passes rate limiter immediately
    const r3 = dosing.submit({ title: "Security Alert", message: "Unauthorized key", urgent: true, whisper: false }, now + 130000, 14);
    expect(r3.status).toBe("dispatched");

    // 4. Quiet hours at 23:00 blocks non-urgent notification
    const r4 = dosing.submit({ title: "Reminder", message: "Water plants", urgent: false, whisper: false }, now + 140000, 23);
    expect(r4.status).toBe("quiet_hours_blocked");

    // 5. Whisper is batched into 18:00 envelope
    const r5 = dosing.submit({ title: "Poem Idea", message: "Night star", urgent: false, whisper: true }, now + 150000, 14);
    expect(r5.status).toBe("batched_whisper");
    expect(dosing.getBatchedWhisperCount()).toBe(1);

    // Flush envelope
    const envelope = dosing.flushWhisperEnvelope();
    expect(envelope).not.toBeNull();
    expect(dosing.getBatchedWhisperCount()).toBe(0);
  });

  it("FR-OS-09 / HotConfig handles 250ms debounce, per-key diff, and fail-closed validation", async () => {
    const bus = new EventBusBridge(9882);
    const config = new HotConfig(bus);

    // Valid update
    const updatePromise = config.applyUpdate({ autonomyLevel: 3 });
    const res = await updatePromise;
    expect(res.applied).toBe(true);
    expect(res.diff["autonomyLevel"].old).toBe(2);
    expect(res.diff["autonomyLevel"].new).toBe(3);
    expect(config.getConfig().autonomyLevel).toBe(3);

    // Invalid update (fail-closed, keeps old value)
    const invalidPromise = config.applyUpdate({ autonomyLevel: 99 as any });
    const invRes = await invalidPromise;
    expect(invRes.applied).toBe(false);
    expect(config.getConfig().autonomyLevel).toBe(3); // Unchanged
  });

  it("FR-OS-12 / NetworkGuard blocks unauthorized outbound sockets (zero-outbound rule)", () => {
    const bus = new EventBusBridge(9883);
    const guard = new NetworkGuard(bus);

    // Localhost allowed
    const local = guard.evaluateOutbound("127.0.0.1", 8765);
    expect(local.allowed).toBe(true);

    // Official signed update endpoint allowed
    const official = guard.evaluateOutbound("updates.trendamis.org", 443);
    expect(official.allowed).toBe(true);

    // Unauthorized external IP / domain BLOCKED
    const rogue = guard.evaluateOutbound("198.51.100.1", 8080);
    expect(rogue.allowed).toBe(false);
    expect(rogue.reason).toContain("blocked by NetworkGuard");
  });

  it("FR-OS-14 / SentryMode triggers on 5-minute idle and sleeps avatar/camera", () => {
    const bus = new EventBusBridge(9884);
    const sentry = new SentryMode(bus);
    const now = Date.now();

    expect(sentry.isActive()).toBe(false);

    // Idle for 6 minutes (360,000 ms)
    const idleDetected = sentry.checkIdle(now + 360000);
    expect(idleDetected).toBe(true);
    expect(sentry.isActive()).toBe(true);

    // Activity resumes
    sentry.recordActivity();
    expect(sentry.isActive()).toBe(false);
  });

  it("FR-OS-13 / BootOrchestrator runs 9 gated steps, emits noctis.boot and noctis.ready", async () => {
    const bus = new EventBusBridge(9885);
    const orchestrator = new BootOrchestrator(bus);
    const emittedEvents: string[] = [];

    bus.subscribe("noctis.*", (evt) => {
      emittedEvents.push(evt.topic);
    });

    const bootRes = await orchestrator.executeBoot();
    expect(bootRes.success).toBe(true);
    expect(bootRes.results.length).toBe(9);
    expect(bootRes.totalDurationMs).toBeLessThan(15000); // < 15s per SRS cold boot

    // Only noctis.boot and noctis.ready permitted
    const uniqueTopics = Array.from(new Set(emittedEvents));
    expect(uniqueTopics.sort()).toEqual(["noctis.boot", "noctis.ready"].sort());
  });

  it("FR-OS-13 / BootOrchestrator halts fail-closed if any step fails", async () => {
    const bus = new EventBusBridge(9886);
    const orchestrator = new BootOrchestrator(bus);

    // Register a broken check at step 4
    orchestrator.registerStep(4, "Broken Model Service", () => false);

    const bootRes = await orchestrator.executeBoot();
    expect(bootRes.success).toBe(false);
    expect(bootRes.failedStep).toBe(4);
  });
});
