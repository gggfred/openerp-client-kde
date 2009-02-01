;NSIS Modern User Interface
;Start Menu Folder Selection Example Script
;Written by Joost Verburg

; In order to compile this installer you'll need:
; a) koo installer (.exe): created with setup.py bdist_wininst
; b) python installer (.msi): download latest from python website
; c) python win32 extensions (.exe): download latest form pywin32 website
; d) pyqt installer (.exe): download latest from pyqt website
; All these files should be placed in the 'nsis' directory. If versions
; have changed you might need to modify 'SecTinyERPClient' with the
; appropiate filenames.
;
; Once compiled you should get a file called 'koo-setup.exe' in the 'nsis' 
; directory.
;
; Enjoy!

;--------------------------------
;Include Modern UI

  !include "MUI.nsh"

;--------------------------------
;General

  ;Name and file
  Name "Koo"
  OutFile "koo-setup.exe"

  ;Default installation folder
  InstallDir "$PROGRAMFILES\Koo"
  
  ;Get installation folder from registry if available
  InstallDirRegKey HKCU "Software\Koo" ""

  ;Vista redirects $SMPROGRAMS to all users without this
  RequestExecutionLevel admin

;--------------------------------
;Variables

  Var MUI_TEMP
  Var STARTMENU_FOLDER

  

;--------------------------------
;Interface Settings

  !define MUI_ABORTWARNING
  
;--------------------------------
;Pages

  !insertmacro MUI_PAGE_WELCOME
  !insertmacro MUI_PAGE_LICENSE "..\doc\LICENCE.txt"
 # !insertmacro MUI_PAGE_COMPONENTS
  !insertmacro MUI_PAGE_DIRECTORY
  
  ;Start Menu Folder Page Configuration
  !define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKCU" 
  !define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\Koo"
  !define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "Koo"
  
  !insertmacro MUI_PAGE_STARTMENU Application $STARTMENU_FOLDER
  
  !insertmacro MUI_PAGE_INSTFILES

  !define MUI_FINISHPAGE_NOAUTOCLOSE
  !define MUI_FINISHPAGE_RUN
  !define MUI_FINISHPAGE_RUN_CHECKED
  !define MUI_FINISHPAGE_RUN_TEXT "Start Koo"
  !define MUI_FINISHPAGE_RUN_FUNCTION "LaunchLink"
  !define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
  !define MUI_FINISHPAGE_SHOWREADME $INSTDIR\README.txt
  !insertmacro MUI_PAGE_FINISH

  
  !insertmacro MUI_UNPAGE_WELCOME
  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
;Languages
 
  !insertmacro MUI_LANGUAGE "English"

;--------------------------------
;Installer Sections

Section "Koo" SecKoo

    SetOutPath "$TEMP"
    File "vcredist_x86.exe"
    ExecWait '"$TEMP\vcredist_x86.exe" /S'

    SetOutPath "$INSTDIR"

    File /r "..\dist\*"

    ;Store installation folder
    WriteRegStr HKCU "Software\Koo" "" $INSTDIR
    
    ;Create uninstaller
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Koo" "DisplayName" "Koo (remove only)"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Koo" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
      
    ;Create shortcuts
    CreateDirectory "$SMPROGRAMS\$STARTMENU_FOLDER"
    CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\Koo.lnk" "$INSTDIR\koo.exe"
    CreateShortCut "$DESKTOP\Koo.lnk" "$INSTDIR\koo.exe"
    !insertmacro MUI_STARTMENU_WRITE_END

SectionEnd

;Descriptions

  ;Language strings
  LangString DESC_SecKoo ${LANG_ENGLISH} "Koo."

  ;Assign language strings to sections
  !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecKoo} $(DESC_SecKoo)
  !insertmacro MUI_FUNCTION_DESCRIPTION_END
 
;--------------------------------
;Uninstaller Section

Section "Uninstall"
  RMDir /r "$INSTDIR"

  !insertmacro MUI_STARTMENU_GETFOLDER Application $MUI_TEMP

  Delete "$SMPROGRAMS\$MUI_TEMP\Koo.lnk"
  Delete "$DESKTOP\Koo.lnk"
  RMDir /r "$SMPROGRAMS\$STARTMENU_FOLDER"

  ;Delete empty start menu parent diretories
  StrCpy $MUI_TEMP "$SMPROGRAMS\$MUI_TEMP"

  startMenuDeleteLoop:
    ClearErrors
    RMDir $MUI_TEMP
    GetFullPathName $MUI_TEMP "$MUI_TEMP\.."

    IfErrors startMenuDeleteLoopDone

    StrCmp $MUI_TEMP $SMPROGRAMS startMenuDeleteLoopDone startMenuDeleteLoop
  startMenuDeleteLoopDone:

  DeleteRegKey HKEY_LOCAL_MACHINE "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Koo"
  DeleteRegKey /ifempty HKCU "Software\Koo"

SectionEnd

Function LaunchLink
  ExecShell "" "$INSTDIR\koo.exe"
FunctionEnd
