<template>
  <div class="w-full h-full flex flex-col px-6 pt-3 pb-5 overflow-y-auto space-y-5 select-none">
    <!-- View Header -->
    <div class="flex items-center justify-between pb-3 border-b border-purple-900/30">
      <div>
        <h2 class="text-xl font-bold text-slate-100 font-serif flex items-center gap-2">
          <span>🔧</span>
          <span>Shadow Hands — Pagar Keamanan & Hak Akses Alat</span>
        </h2>
        <p class="text-xs text-purple-300/70 mt-0.5">
          Matriks Zero-Trust: Setiap tindakan destructive memerlukan izin eksplisit Young Lord.
        </p>
      </div>
      <div class="flex items-center gap-2">
        <span class="px-3 py-1 rounded-full text-xs font-medium bg-emerald-950/60 border border-emerald-500/40 text-emerald-300">
          ActionGate: Fail-Closed
        </span>
      </div>
    </div>

    <!-- Security Model Banner -->
    <div class="p-4 rounded-2xl bg-gradient-to-r from-purple-950/40 via-indigo-950/40 to-slate-950/60 border border-purple-800/30 flex items-center justify-between">
      <div class="space-y-1">
        <div class="text-xs font-bold text-slate-100 flex items-center gap-2">
          <span>🛡️</span>
          <span>Blood Contract Model & PathJail Strict</span>
        </div>
        <p class="text-[11px] text-purple-200/80 leading-relaxed max-w-2xl">
          Alat-alat destruktif tidak pernah diizinkan beroperasi di luar direktori kerja (PathJail) atau tanpa approval token yang telah diaudit oleh kognisi.
        </p>
      </div>
      <div class="text-right font-mono text-[11px] text-purple-300 shrink-0">
        <div>KillSwitch SLA: &lt; 200ms</div>
        <div class="text-emerald-400">Status: Siaga Terjaga</div>
      </div>
    </div>

    <!-- Tool Items Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3.5">
      <div
        v-for="tool in tools"
        :key="tool.name"
        class="p-4 rounded-2xl bg-[#100c24]/80 border border-purple-900/30 space-y-2 flex flex-col justify-between"
      >
        <div class="flex items-center justify-between">
          <span class="font-mono font-bold text-xs text-purple-200">{{ tool.name }}</span>
          <span
            class="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase"
            :class="badgeClass(tool.level)"
          >
            {{ tool.level }}
          </span>
        </div>
        <p class="text-[11px] text-purple-300/80 leading-relaxed">{{ tool.desc }}</p>
        <div class="pt-2 border-t border-purple-900/20 text-[10px] text-slate-400 font-mono flex justify-between">
          <span>Pemberi Izin: <strong>{{ tool.authority }}</strong></span>
          <span>Scope: <strong>{{ tool.scope }}</strong></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const tools = [
  {
    name: 'camera.capture',
    level: 'LOCAL ONLY',
    desc: 'Sensor optik YuNet & SFace 128-d. Haram dirutekan remote demi privasi mutlak.',
    authority: 'Hardware Lokal',
    scope: 'Mata Desktop',
  },
  {
    name: 'microphone.capture',
    level: 'LOCAL ONLY',
    desc: 'Tangkapan suara lokal Faster-Whisper VAD. Pemrosesan audio di memori privat.',
    authority: 'Hardware Lokal',
    scope: 'Telinga Saraf',
  },
  {
    name: 'filesystem.read',
    level: 'PATH JAIL',
    desc: 'Membaca berkas kode & dokumen hanya di dalam workspace sah pengguna.',
    authority: 'PathJail Guard',
    scope: 'c:\\Traine\\ruka',
  },
  {
    name: 'filesystem.write',
    level: 'APPROVAL REQUIRED',
    desc: 'Menulis, memperbarui, atau menghapus berkas proyek melalui audit multi-file diff.',
    authority: 'Young Lord',
    scope: 'Workspace Sah',
  },
  {
    name: 'terminal.execute',
    level: 'APPROVAL REQUIRED',
    desc: 'Eksekusi perintah terminal shell / powershell dengan pengawasan timeout ketat.',
    authority: 'Young Lord',
    scope: 'Subprocess Jail',
  },
  {
    name: 'git.commit',
    level: 'REMOTE OK',
    desc: 'Pencatatan status version control dan pembuatan pesan commit berstandar.',
    authority: 'Git Subsystem',
    scope: 'Repository Lokal',
  },
];

function badgeClass(level: string) {
  if (level === 'LOCAL ONLY') return 'bg-emerald-950/70 border border-emerald-500/40 text-emerald-300';
  if (level === 'PATH JAIL') return 'bg-purple-950/70 border border-purple-500/40 text-purple-300';
  if (level === 'APPROVAL REQUIRED') return 'bg-amber-950/70 border border-amber-500/40 text-amber-300';
  return 'bg-cyan-950/70 border border-cyan-500/40 text-cyan-300';
}
</script>
