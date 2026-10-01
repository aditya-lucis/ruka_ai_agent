!macro customInstall
  DetailPrint "Menambahkan Ruka CLI ke Windows System PATH..."
  ReadRegStr $0 HKCU "Environment" "Path"
  WriteRegExpandStr HKCU "Environment" "Path" "$0;$INSTDIR;$INSTDIR\resources\brain"
  SendMessage 65535 26 0 "STR:Environment" /TIMEOUT=5000
!macroend

!macro customUnInstall
  SendMessage 65535 26 0 "STR:Environment" /TIMEOUT=5000
!macroend
