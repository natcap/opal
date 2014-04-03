!define TITLE "${APP_NAME} ${VERSION} ${APP_ARCHITECTURE}"
!define APP_VERSION "${VERSION}"
!define APP_ARCHITECTURE "${ARCHITECTURE}"
!define APP_NAME "Adept"

; GENERAL APPLICATION INFORMATION VARIABLES
!define INTERNAL_NAME "${APP_NAME}"
!define INTERNAL_VERSION "${APP_VERSION}"
!define INTERNAL_ARCHITECTURE "${APP_ARCHITECTURE}"
!define PUBLISHER "The Natural Capital Project"
!define WEBSITE "http://www.naturalcapitalproject.org"


; INSTALLER INFORMATION
!define INSTALLER_TITLE "${TITLE}"
#!define BUILD_FOLDER "..\adept_py2exe"
#!define BUILD_FOLDER "..\data\colombia_static_data"
!define BUILD_FOLDER "${PY2EXE_FOLDER}"
!define INSTALLER_FILENAME "${APP_NAME}_${VERSION}_${APP_ARCHITECTURE}_Setup.exe"
!define INSTALLER_LOGFILE "install_log.txt"
!define INSTALLER_ICON "installer_icon.png"
!define DEFAULT_INSTALL_DIR "C:\Program Files\${TITLE}"
!define LICENSE_FILE "..\LICENSE.TXT"
!define START_MENU_FOLDER "$SMPROGRAMS\${INTERNAL_NAME} ${INTERNAL_VERSION}"


; UNINSTALLER INFORMATION
!define UNINSTALLER_FILENAME "Uninstall ${APP_NAME} ${APP_VERSION}"
!define REGISTRY_PATH "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PUBLISHER} ${INTERNAL_NAME} ${INTERNAL_VERSION}"


; Set the compression size and type.
SetCompressor /FINAL /SOLID lzma
SetCompressorDictSize 64

; MUI 1.67 compatible macro settings------
; Installer settings.
!include "MUI.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"

; MUI installer pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE ${LICENSE_FILE}
!insertmacro MUI_PAGE_DIRECTORY

; MUI uninstaller pages
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

Name "${INTERNAL_NAME} ${VERSION}"
OutFile "${INSTALLER_FILENAME}"
InstallDir "${DEFAULT_INSTALL_DIR}"
ShowInstDetails show

Var DataDirPath

Function .onInit
!insertmacro MUI_LANGDLL_DISPLAY
System::Call "kernel32::GetCurrentDirectory(i ${NSIS_MAX_STRLEN}, t .r0)"
StrCpy $DataDirPath "$0\data" ; Default folder for the data folder selection dialog
#nsDialogs::SelectFolderDialog "SELECT FOLDER" "C:\data"
FunctionEnd

;PageEx Directory
;    DirVar $DataDirPath
;    PageCallbacks DataPageShow "" DataPageLeave
;    DirText "Select data folder" "Data Folder" "" "Select data folder"
;    DirVerify leave
;PageExEnd
;
;Function DataPageShow
;    ;Hide space texts
;    FindWindow $0 "#32770" "" $HWNDPARENT
;    GetDlgItem $1 $0 0x3FF
;    ShowWindow $1 0
;    GetDlgItem $1 $0 0x400
;    ShowWindow $1 0
;FunctionEnd
;
;Function DataPageLeave
;    GetInstDirError $0
;    ${If} $0 <> 0
;    ${OrIfNot} ${FileExists} "$DataDirPath"
;        MessageBox mb_iconstop "You must locate the php folder to continue!"
;        Abort
;    ${EndIf}
;FunctionEnd

!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
; At least one language is required
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Spanish"



; This function (and these couple variables) allow us to dump the NSIS
; Installer log to a log file of our choice, which is very handy for debugging.
; To use, call it like this in the installation section.:
;
;   StrCpy $0 "$INSTDIR\install_log.txt"
;   Push $0
;   Call DumpLog
;
!define LVM_GETITEMCOUNT 0x1004
!define LVM_GETITEMTEXT 0x102D

Function DumpLog
    Exch $5
    Push $0
    Push $1
    Push $2
    Push $3
    Push $4
    Push $6

    FindWindow $0 "#32770" "" $HWNDPARENT
    GetDlgItem $0 $0 1016
    StrCmp $0 0 exit
    FileOpen $5 $5 "w"
    StrCmp $5 "" exit
        SendMessage $0 ${LVM_GETITEMCOUNT} 0 0 $6
        System::Alloc ${NSIS_MAX_STRLEN}
        Pop $3
        StrCpy $2 0
        System::Call "*(i, i, i, i, i, i, i, i, i) i \
            (0, 0, 0, 0, 0, r3, ${NSIS_MAX_STRLEN}) .r1"
        loop: StrCmp $2 $6 done
            System::Call "User32::SendMessageA(i, i, i, i) i \
            ($0, ${LVM_GETITEMTEXT}, $2, r1)"
            System::Call "*$3(&t${NSIS_MAX_STRLEN} .r4)"
            FileWrite $5 "$4$\r$\n"
            IntOp $2 $2 + 1
            Goto loop
        done:
            FileClose $5
            System::Free $1
            System::Free $3
    exit:
        Pop $6
        Pop $4
        Pop $3
        Pop $2
        Pop $1
        Pop $0
        Exch $5
FunctionEnd
    
Section "Install" SEC01

  SetShellVarContext all
  SetOutPath "$INSTDIR"
  writeUninstaller "$INSTDIR\${UNINSTALLER_FILENAME}.exe"

  ; Desired files are up one directory and in the given build folder.
  File /r "${BUILD_FOLDER}\*"
    CreateDirectory "${START_MENU_FOLDER}"
CreateShortCut "${START_MENU_FOLDER}\${APP_NAME}.lnk" "$INSTDIR\run_adept.exe" "${icon}"
CreateShortCut "${START_MENU_FOLDER}\${APP_NAME} Documentation.lnk" "$INSTDIR\adept_documentation.docx" ""

    WriteRegStr HKLM "${REGISTRY_PATH}" "DisplayName"          "${APP_NAME} ${APP_VERSION}"
    WriteRegStr HKLM "${REGISTRY_PATH}" "UninstallString"      "$INSTDIR\${UNINSTALLER_FILENAME}.exe"
    WriteRegStr HKLM "${REGISTRY_PATH}" "QuietUninstallString" "$INSTDIR\${UNINSTALLER_FILENAME}.exe /S"
    WriteRegStr HKLM "${REGISTRY_PATH}" "InstallLocation"      "$INSTDIR"
    WriteRegStr HKLM "${REGISTRY_PATH}" "DisplayIcon"          "$INSTDIR\${ICON}"
    WriteRegStr HKLM "${REGISTRY_PATH}" "Publisher"            "${PUBLISHER}"
    WriteRegStr HKLM "${REGISTRY_PATH}" "URLInfoAbout"         "${WEBSITE}"
    WriteRegStr HKLM "${REGISTRY_PATH}" "DisplayVersion"       "${APP_VERSION}"
    WriteRegDWORD HKLM "${REGISTRY_PATH}" "NoModify" 1
    WriteRegDWORD HKLM "${REGISTRY_PATH}" "NoRepair" 1

    ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
    ;CUSTOM CODE HERE

    SetOutPath "$INSTDIR"
    File ..\dist\*.zip
    CreateDirectory "$INSTDIR\data"
    CreateDirectory "$INSTDIR\data\colombia_static_data"
    SetOutPath "$INSTDIR\data\colombia_static_data\"
    nsisunz::UnzipToLog "$INSTDIR\static_data.zip" "."

    CreateDirectory "$INSTDIR\data\colombia_tool_data"
    SetOutPath "$INSTDIR\data\colombia_tool_data\"
    nsisunz::UnzipToLog "$INSTDIR\tool_data.zip" "."

    ;END OF CUSTOM UNZIPPING
    
    ; Write the install log to a text file on disk.
    StrCpy $0 "$INSTDIR\${INSTALLER_LOGFILE}"
    Push $0
    Call DumpLog
    
SectionEnd

Section "uninstall"
    ; Need to enforce execution level as admin.  See
    ; nsis.sourceforge.net/Shortcuts_removal_fails_on_Windows_Vista
    SetShellVarContext all
    rmdir /r "${START_MENU_FOLDER}"

    ; Delete the installation directory on disk
    rmdir /r "$INSTDIR"

    ; Delete the entire registry key for this version of RIOS.
    DeleteRegKey HKLM "${REGISTRY_PATH}"
SectionEnd
