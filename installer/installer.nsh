!macro customInit
  ; Tutup proses Ruka & Noctis yang masih berjalan agar tidak ada file lock yang menyebabkan error instalasi / corrupt
  nsExec::Exec 'cmd /c taskkill /f /im Ruka.exe /t >nul 2>&1'
  nsExec::Exec 'cmd /c taskkill /f /im ruka-brain.exe /t >nul 2>&1'
  nsExec::Exec 'cmd /c taskkill /f /im noctis-kernel.exe /t >nul 2>&1'
  nsExec::Exec 'cmd /c taskkill /f /im ruka.exe /t >nul 2>&1'
!macroend

!macro customInstall
  DetailPrint "Menyiapkan Ruka GUI command (ruka-gui.cmd)..."
  FileOpen $9 "$INSTDIR\resources\brain\ruka-gui.cmd" w
  FileWrite $9 '@echo off$\r$\n'
  FileWrite $9 'start "" "%~dp0..\..\Ruka.exe" %*$\r$\n'
  FileClose $9

  DetailPrint "Menambahkan Ruka CLI ke Windows User PATH (deduplikasi)..."
  nsExec::Exec 'powershell -NoProfile -ExecutionPolicy Bypass -Command "$target = ''$INSTDIR\resources\brain''; $curr = [Environment]::GetEnvironmentVariable(''Path'', ''User''); if (-not ($curr -split '';'' | Where-Object { $_ -eq $target })) { $new = ($curr.TrimEnd('';'') + '';'' + $target).TrimStart('';''); [Environment]::SetEnvironmentVariable(''Path'', $new, ''User'') }"'
  SendMessage 65535 26 0 "STR:Environment" $1 /TIMEOUT=2000
!macroend

!macro customUnInstall
  nsExec::Exec 'cmd /c taskkill /f /im Ruka.exe /t >nul 2>&1'
  nsExec::Exec 'cmd /c taskkill /f /im ruka-brain.exe /t >nul 2>&1'
  nsExec::Exec 'cmd /c taskkill /f /im noctis-kernel.exe /t >nul 2>&1'
  nsExec::Exec 'cmd /c taskkill /f /im ruka.exe /t >nul 2>&1'
  Delete "$INSTDIR\resources\brain\ruka-gui.cmd"
  DetailPrint "Membersihkan Ruka CLI dari Windows User PATH..."
  nsExec::Exec 'powershell -NoProfile -ExecutionPolicy Bypass -Command "$target = ''$INSTDIR\resources\brain''; $curr = [Environment]::GetEnvironmentVariable(''Path'', ''User''); if ($curr) { $clean = ($curr -split '';'' | Where-Object { $_ -ne $target -and $_.Trim() -ne '''' }) -join '';''; [Environment]::SetEnvironmentVariable(''Path'', $clean, ''User'') }"'
  SendMessage 65535 26 0 "STR:Environment" $1 /TIMEOUT=2000
!macroend

