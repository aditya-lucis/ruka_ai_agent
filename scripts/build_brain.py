# -*- coding: utf-8 -*-
"""Script pembangun mandiri (Zero-Dependency Standalone Bundler) untuk Otak Python Ruka.
Mengompilasi launcher.py dan seluruh dependensi AI/Kognisi/Wicara/Vision menjadi
binary mandiri (ruka-brain.exe) ke dalam direktori desktop/resources/brain.
"""
from __future__ import annotations

import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DESKTOP_DIR = ROOT_DIR / "desktop"
RESOURCES_DIR = DESKTOP_DIR / "resources"
TARGET_BRAIN_DIR = RESOURCES_DIR / "brain"
BUILD_DIR = ROOT_DIR / "build" / "pyinstaller"
DIST_TMP = ROOT_DIR / "build" / "dist"


def main():
    print("=" * 70)
    print(" [RUKA BUNDLER] Membangun Standalone Self-Contained Brain")
    print("=" * 70)

    # 1. Bersihkan direktori build lama jika ada
    if TARGET_BRAIN_DIR.exists():
        print(f"[*] Membersihkan folder lama: {TARGET_BRAIN_DIR}")
        shutil.rmtree(TARGET_BRAIN_DIR, ignore_errors=True)

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    DIST_TMP.mkdir(parents=True, exist_ok=True)

    # 2. Siapkan argumen PyInstaller berbasis ruka-brain.spec portabel
    spec_file = ROOT_DIR / "ruka-brain.spec"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        f"--workpath={BUILD_DIR}",
        f"--distpath={DIST_TMP}",
        str(spec_file),
    ]

    print(f"[*] Menjalankan PyInstaller compilation berbasis {spec_file.name}...")
    res = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if res.returncode != 0:
        print(f"[!] PyInstaller gagal dengan kode: {res.returncode}")
        sys.exit(res.returncode)

    # 3. Pindahkan hasil build ke desktop/resources/brain
    compiled_folder = DIST_TMP / "ruka-brain"
    if not compiled_folder.exists():
        print(f"[!] Folder hasil kompilasi tidak ditemukan di {compiled_folder}")
        sys.exit(1)

    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[*] Memindahkan hasil ke {TARGET_BRAIN_DIR}...")
    shutil.move(str(compiled_folder), str(TARGET_BRAIN_DIR))

    # 4. Sertakan berkas konfigurasi (.env) jika tersedia
    env_src = ROOT_DIR / "ruka-agent" / ".env"
    if env_src.exists():
        env_dest = TARGET_BRAIN_DIR / ".env"
        print(f"[*] Menyalin konfigurasi .env ke {env_dest}...")
        shutil.copy2(str(env_src), str(env_dest))

    # 5. Sertakan seed database ruka.db jika tersedia
    db_src = ROOT_DIR / "ruka.db"
    if db_src.exists():
        db_dest = TARGET_BRAIN_DIR / "ruka.db"
        print(f"[*] Menyalin seed memory database ke {db_dest}...")
        shutil.copy2(str(db_src), str(db_dest))

    # 5b. Sertakan model offline whisper.cpp jika tersedia
    local_appdata = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    whisper_candidates = [
        local_appdata / "pywhispercpp" / "pywhispercpp" / "models" / "ggml-tiny.bin",
        Path.home() / ".cache" / "whisper.cpp" / "ggml-tiny.bin",
    ]
    model_src = next((p for p in whisper_candidates if p.exists()), None)
    if model_src:
        models_dest_dir = TARGET_BRAIN_DIR / "models"
        models_dest_dir.mkdir(parents=True, exist_ok=True)
        print(f"[*] Menyalin model offline whisper.cpp ({model_src.name}) ke {models_dest_dir}...")
        shutil.copy2(str(model_src), str(models_dest_dir / "ggml-tiny.bin"))

    # 5d. Sertakan folder skills/ mandiri
    skills_src = ROOT_DIR / "skills"
    if skills_src.exists():
        skills_dest = TARGET_BRAIN_DIR / "skills"
        print(f"[*] Menyalin folder skills/ ke {skills_dest}...")
        shutil.copytree(str(skills_src), str(skills_dest), dirs_exist_ok=True)

    # 5c. Kompilasi Ruka CLI Terminal Executable (ruka.exe)
    cli_script = ROOT_DIR / "ruka_cli.py"
    if cli_script.exists():
        print("[*] Mengompilasi Ruka CLI Executable (ruka.exe)...")
        cli_cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--onefile",
            "--console",
            "--name=ruka",
            f"--workpath={BUILD_DIR}",
            f"--distpath={DIST_TMP}",
            str(cli_script),
        ]
        res_cli = subprocess.run(cli_cmd, cwd=str(ROOT_DIR))
        cli_exe_src = DIST_TMP / "ruka.exe"
        if res_cli.returncode == 0 and cli_exe_src.exists():
            cli_dest = TARGET_BRAIN_DIR / "ruka.exe"
            print(f"[*] Menyalin ruka.exe ke {cli_dest}...")
            shutil.copy2(str(cli_exe_src), str(cli_dest))

    # 6. Verifikasi keberadaan ruka-brain.exe dan ruka.exe
    brain_exe = TARGET_BRAIN_DIR / "ruka-brain.exe"
    cli_exe = TARGET_BRAIN_DIR / "ruka.exe"
    if brain_exe.exists():
        print("=" * 70)
        print(" [RUKA BUNDLER] BERHASIL!")
        print(f" Binary Standalone Brain: {brain_exe}")
        print(f" Binary Terminal CLI   : {cli_exe}")
        print(" Ruka kini membawa 100% otaknya dan CLI 'ruka' ke semua PC!")
        print("=" * 70)
    else:
        print(f"[!] ruka-brain.exe tidak ditemukan di {TARGET_BRAIN_DIR}")
        sys.exit(1)


if __name__ == "__main__":
    main()
