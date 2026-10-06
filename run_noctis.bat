@echo off
setlocal enabledelayedexpansion
title PROJECT NOCTIS — Marquis of Trendamis (Ruka Companion OS)

echo ===============================================================================
echo   PROJECT NOCTIS : MARQUIS OF TRENDAMIS AI COMPANION OS
echo   Unified Three-Tier Architecture: Electron + Bun TypeScript + Python Brain
echo   100%% Local-First, Zero-Paid Tools, Zero Outbound Sockets
echo ===============================================================================
echo.

:: 1. Cek direktori runtime
set "RUNTIME_DIR=%LOCALAPPDATA%\ruka\runtime"
if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%"

:: 2. Boot Bun Kernel (EventBus V3 Bridge & Organ Watchdog)
echo [*] Memeriksa status Noctis Kernel (Bun / Standalone)...
set "KERNEL_EXE=%~dp0noctis\bin\noctis-kernel.exe"
if exist "%KERNEL_EXE%" (
    echo [*] Meluncurkan Standalone Noctis Kernel: %KERNEL_EXE%
    start "" /B "%KERNEL_EXE%"
) else (
    echo [*] Meluncurkan Bun Kernel dari source: bun run src/index.ts
    start "" /B bun run "%~dp0noctis\kernel\src\index.ts"
)

:: 3. Boot Python Brain Host (launcher.py)
echo [*] Memeriksa status Python Brain Host (launcher.py)...
start "" /B python "%~dp0launcher.py"

:: 4. Beri jeda 2 detik untuk handshake port IPC & EventBus
timeout /t 2 /nobreak >nul

:: 5. Luncurkan Desktop Shell (Electron Presentation Layer)
echo [*] Meluncurkan Electron Desktop Companion Shell...
cd /d "%~dp0desktop"
npm start

echo [*] Sesi Project Noctis selesai. Marquis of Trendamis beristirahat.
