!include "MUI2.nsh"
Name "Yemen AI"
OutFile "Yemen_AI_Setup.exe"
InstallDir "$PROGRAMFILES64\Yemen AI"
RequestExecutionLevel admin
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
Section "Install"
SetOutPath "$INSTDIR"
File /r "..\dist\Yemen_AI\*.*"
CreateShortcut "$DESKTOP\Yemen AI.lnk" "$INSTDIR\Yemen_AI.exe"
CreateDirectory "$SMPROGRAMS\Yemen AI"
CreateShortcut "$SMPROGRAMS\Yemen AI\Yemen AI.lnk" "$INSTDIR\Yemen_AI.exe"
WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd
Section "Uninstall"
Delete "$DESKTOP\Yemen AI.lnk"
RMDir /r "$SMPROGRAMS\Yemen AI"
RMDir /r "$INSTDIR"
SectionEnd
