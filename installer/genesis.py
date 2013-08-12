"""Genesis - NSIS generator"""

import demjson  # using for js compaibility -- comments in JSON files.
import sys

LOG_FILE_SCRIPT = """
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
        System::Call "*(i, i, i, i, i, i, i, i, i) i \\
            (0, 0, 0, 0, 0, r3, ${NSIS_MAX_STRLEN}) .r1"
        loop: StrCmp $2 $6 done
            System::Call "User32::SendMessageA(i, i, i, i) i \\
            ($0, ${LVM_GETITEMTEXT}, $2, r1)"
            System::Call "*$3(&t${NSIS_MAX_STRLEN} .r4)"
            FileWrite $5 "$4$\\r$\\n"
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
    """

SAVE_LOG_FILE = """
    ; Write the install log to a text file on disk.
    StrCpy $0 "$INSTDIR\\${INSTALLER_LOGFILE}"
    Push $0
    Call DumpLog
    """

UNINSTALLER_SECTION = """
Section "uninstall"
    ; Need to enforce execution level as admin.  See
    ; nsis.sourceforge.net/Shortcuts_removal_fails_on_Windows_Vista
    SetShellVarContext all
    rmdir /r "$SMPROGRAMS\${START_MENU_FOLDER}"

    ; Delete the installation directory on disk
    rmdir /r "$INSTDIR"

    ; Delete the entire registry key for this version of RIOS.
    DeleteRegKey HKLM "${REGISTRY_PATH}"
SectionEnd
"""

UNINSTALLER_REG_KEYS = """
    WriteRegStr HKLM "${REGISTRY_PATH}" "DisplayName"          "${APP_NAME} ${APP_VERSION}"
    WriteRegStr HKLM "${REGISTRY_PATH}" "UninstallString"      "$INSTDIR\\${UNINSTALLER_FILENAME}.exe"
    WriteRegStr HKLM "${REGISTRY_PATH}" "QuietUninstallString" "$INSTDIR\\${UNINSTALLER_FILENAME}.exe /S"
    WriteRegStr HKLM "${REGISTRY_PATH}" "InstallLocation"      "$INSTDIR"
    WriteRegStr HKLM "${REGISTRY_PATH}" "DisplayIcon"          "$INSTDIR\\${ICON}"
    WriteRegStr HKLM "${REGISTRY_PATH}" "Publisher"            "${PUBLISHER}"
    WriteRegStr HKLM "${REGISTRY_PATH}" "URLInfoAbout"         "${WEBSITE}"
    WriteRegStr HKLM "${REGISTRY_PATH}" "DisplayVersion"       "${APP_VERSION}"
    WriteRegDWORD HKLM "${REGISTRY_PATH}" "NoModify" 1
    WriteRegDWORD HKLM "${REGISTRY_PATH}" "NoRepair" 1
    """

def build_installer_script(config_file_uri, out_file_uri):
    new_file = open(out_file_uri, 'w')
    config_dict = demjson.decode(open(config_file_uri).read())

    # check for default values before writing the script.
    sanitized_config = check_defaults(config_dict)

    new_file.write(local_variables(sanitized_config))
    new_file.write(general_settings())
    new_file.write(languages(sanitized_config['general']['languages']))
    new_file.write(installer_init(sanitized_config['general']['languages']))

    if sanitized_config['installer']['save_log']:
        new_file.write(LOG_FILE_SCRIPT)

    #TODO: write the .onInit function

    new_file.write(installer(sanitized_config['installer']))
    new_file.write(UNINSTALLER_SECTION)

    new_file.close()

def check_defaults(config_dictionary):
    # Assume that everything needed is there for now.
    # TODO: actually sanitize the config dictionary.  Raise needed exceptions,
    # or else assume certain defaults.
    return config_dictionary

def languages(lang_list):
    language_string = "; At least one language is required\n"

    # if no languages specified, assume english
    if len(lang_list) == 0:
        lang_list.append("English")

    for language in lang_list:
        language_string += "!insertmacro MUI_LANGUAGE \"%s\"\n" % language

    language_string += "\n\n"
    return language_string

def installer_init(lang_list):
    init_string = "Function .onInit\n"
    if len(lang_list) > 1:
        init_string += "!insertmacro MUI_LANGDLL_DISPLAY\n"
    init_string += "FunctionEnd\n"
    return init_string

def uninstaller_init():
    return """
Function un.onInit
FunctionEnd
"""

def installer_pages():
    pages_string = """
; MUI installer pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE ${LICENSE_FILE}
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
"""
    return pages_string

def uninstaller_pages():
    pages_string = """
; MUI uninstaller pages
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
"""
    return pages_string

def general_settings():
    general_settings = """
; Set the compression size and type.
SetCompressor /FINAL /SOLID lzma
SetCompressorDictSize 64

; MUI 1.67 compatible macro settings------
; Installer settings.
!include "MUI.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"
"""

    general_settings += installer_pages()
    general_settings += uninstaller_pages()
    general_settings += """
Name "${APP_NAME} ${APP_VERSION}"
OutFile "${INSTALLER_FILENAME}"
InstallDir "${DEFAULT_INSTALL_DIR}"
ShowInstDetails show
"""
    return general_settings


def local_variables(options):
    custom_vars = []
    for var_name, var_value in options['variables'].iteritems():
        custom_vars.append('!define %s "%s"' % (var_name, var_value))

    strings = [
        '; GENERAL APPLICATION INFORMATION VARIABLES',
        '!define PUBLISHER "%s"' % options['general']['publisher'],
        '!define WEBSITE "%s"' % options['general']['website'],
        '',
        '',
        '; INSTALLER INFORMATION',
        '!define INSTALLER_TITLE "${APP_NAME} ${APP_VERSION}"',
        '!define BUILD_FOLDER "%s"' % options['general']['build_folder'],
        '!define INSTALLER_FILENAME "${APP_NAME}_${APP_VERSION}_Setup.exe"',
        '!define INSTALLER_LOGFILE "%s"' % options['installer']['install_log'],
        '!define INSTALLER_ICON "%s"' % options['installer']['icon'],
        '!define DEFAULT_INSTALL_DIR "%s"' % options['installer']['install_dir'],
        '!define LICENSE_FILE "%s"' % options['installer']['license'],
        '!define START_MENU_FOLDER "${APP_NAME} ${APP_VERSION}"',
        '',
        '',
        '; UNINSTALLER INFORMATION',
        '!define UNINSTALLER_FILENAME "%s"' % options['uninstaller']['filename'],
        '!define REGISTRY_PATH "%s"' % (
            'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\'
            '${PUBLISHER} ${APP_NAME} ${APP_VERSION}'),
        '',
        '']

    formatted_string = '\n'.join(custom_vars)
    formatted_string += '\n'.join(strings)
    return formatted_string

def start_menu_links(options):
    formatted_string = ''
    # print them verbatim for now.
    for link_data in options:
        link_path = "${START_MENU_FOLDER}\\%s.lnk" % link_data['name']
        link_target = "$INSTDIR\\%s" % link_data['target']

        try:
            link_icon = link_data['icon']
        except KeyError:
            link_icon = ''

        formatted_string += "CreateShortCut \"%s\" \"%s\" \"%s\"\n" % (link_path,
                link_target, link_icon)

    return formatted_string

def installer(installer_options):
    formatted_string = """
Section \"Install\" SEC01\n
  SetShellVarContext all
  SetOutPath "$INSTDIR"
  writeUninstaller "$INSTDIR\${UNINSTALLER_FILENAME}.exe"

  ; Desired files are up one directory and in the given build folder.
  File /r "${BUILD_FOLDER}\*"
    """

    formatted_string += start_menu_links(installer_options['start_menu'])
    formatted_string += UNINSTALLER_REG_KEYS

    if installer_options['save_log']:
        formatted_string += SAVE_LOG_FILE

    formatted_string += """
SectionEnd
"""

    return formatted_string

