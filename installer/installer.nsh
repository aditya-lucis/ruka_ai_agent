!macro customInstall
  DetailPrint "Menyiapkan Ruka GUI command (ruka-gui.cmd)..."
  FileOpen $9 "$INSTDIR\resources\brain\ruka-gui.cmd" w
  FileWrite $9 '@echo off$\r$\n'
  FileWrite $9 'start "" "%~dp0..\..\Ruka.exe" %*$\r$\n'
  FileClose $9

  DetailPrint "Menambahkan Ruka CLI ke Windows System PATH..."
  ReadRegStr $0 HKCU "Environment" "Path"
  WriteRegExpandStr HKCU "Environment" "Path" "$0;$INSTDIR\resources\brain"
  SendMessage 65535 26 0 "STR:Environment" $1 /TIMEOUT=2000
!macroend

!macro customUnInstall
  Delete "$INSTDIR\resources\brain\ruka-gui.cmd"
  SendMessage 65535 26 0 "STR:Environment" $1 /TIMEOUT=2000
!macroend
