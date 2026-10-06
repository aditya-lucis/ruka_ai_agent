/**
 * Action Registry — TypeScript on Bun Runtime
 * Implements SRS FR-OS-04 & SAD Section 4.1
 * - Single implementation shared across Command Palette (Ctrl+Space), Mini Menu, and Tray Ring
 * - Fuzzy search returning at most 8 items
 */

import { ActionItem } from "./types";

export class ActionRegistry {
  private actions: Map<string, ActionItem> = new Map();

  constructor() {
    this.registerDefaultActions();
  }

  public register(action: ActionItem): void {
    this.actions.set(action.id, action);
  }

  public unregister(id: string): void {
    this.actions.delete(id);
  }

  public get(id: string): ActionItem | undefined {
    return this.actions.get(id);
  }

  public getAll(): ActionItem[] {
    return Array.from(this.actions.values());
  }

  /**
   * Search actions with fuzzy matching, returning strictly up to 8 results per FR-OS-04
   */
  public search(query: string, maxResults: number = 8): ActionItem[] {
    if (!query || query.trim() === "") {
      return Array.from(this.actions.values()).slice(0, maxResults);
    }

    const q = query.toLowerCase().trim();
    const scored: { action: ActionItem; score: number }[] = [];

    for (const action of this.actions.values()) {
      const titleLower = action.title.toLowerCase();
      const catLower = action.category.toLowerCase();

      let score = 0;
      if (titleLower === q) score += 100;
      else if (titleLower.startsWith(q)) score += 50;
      else if (titleLower.includes(q)) score += 25;
      else if (catLower.includes(q)) score += 10;
      else {
        // Simple subsequence matching
        let qi = 0;
        for (let i = 0; i < titleLower.length && qi < q.length; i++) {
          if (titleLower[i] === q[qi]) qi++;
        }
        if (qi === q.length) score += 5;
      }

      if (score > 0) {
        scored.push({ action, score });
      }
    }

    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, maxResults).map((s) => s.action);
  }

  public async execute(id: string): Promise<any> {
    const action = this.actions.get(id);
    if (!action) {
      throw new Error(`Action '${id}' not found`);
    }
    return await action.handler();
  }

  private registerDefaultActions(): void {
    this.register({
      id: "noctis.kill_switch",
      title: "Emergency Kill Switch (Matikan Seluruh Aksi)",
      shortcut: "Ctrl+Shift+K",
      category: "system",
      riskLevel: "red",
      handler: () => ({ status: "KILL_SWITCH_ENGAGED" }),
    });

    this.register({
      id: "noctis.open_inspector",
      title: "Buka Inspektur Istana Memori (Memory Palace Inspector)",
      shortcut: "Ctrl+M",
      category: "memory",
      riskLevel: "green",
      handler: () => ({ status: "INSPECTOR_OPENED" }),
    });

    this.register({
      id: "noctis.toggle_avatar",
      title: "Sembunyikan / Tampilkan Avatar Mini",
      shortcut: "Ctrl+H",
      category: "companion",
      riskLevel: "green",
      handler: () => ({ status: "AVATAR_TOGGLED" }),
    });

    this.register({
      id: "noctis.forget_today",
      title: "Lupakan Memori Hari Ini (Idempoten)",
      category: "memory",
      riskLevel: "yellow",
      handler: () => ({ status: "TODAY_MEMORIES_PURGED" }),
    });

    this.register({
      id: "noctis.hot_reload_config",
      title: "Muat Ulang Konfigurasi Panas",
      shortcut: "Ctrl+R",
      category: "settings",
      riskLevel: "green",
      handler: () => ({ status: "CONFIG_RELOADED" }),
    });

    this.register({
      id: "noctis.start_autonomous_shift",
      title: "Mulai Shift Otonomi 4 Jam",
      category: "code",
      riskLevel: "yellow",
      handler: () => ({ status: "AUTONOMOUS_SHIFT_STARTED" }),
    });

    this.register({
      id: "noctis.toggle_sentry",
      title: "Mode Penjaga (Sentry Mode)",
      category: "system",
      riskLevel: "green",
      handler: () => ({ status: "SENTRY_MODE_TOGGLED" }),
    });

    this.register({
      id: "noctis.open_design_lab",
      title: "Buka Crimson Astral Forge & Design Lab",
      category: "code",
      riskLevel: "green",
      handler: () => ({ status: "DESIGN_LAB_OPENED" }),
    });
  }
}
