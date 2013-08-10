"""Genesis - NSIS generator"""

import demjson  # using for js compaibility -- comments in JSON files.
import sys

def build_installer_script(config_file_uri, out_file_uri):
    new_file = open(out_file_uri, 'w')
    config_dict = demjson.decode(open(config_file_uri).read())

    # check for default values before writing the script.
    sanitized_config = check_defaults(config_dict)


def check_defaults(config_dictionary):
    # Assume that everything needed is there for now.
    # TODO: actually sanitize the config dictionary.  Raise needed exceptions,
    # or else assume certain defaults.
    return config_dictionary

def local_variables(options):
    # version
    # architecture
    # build folder
    # uninstaller file name
    # publisher
    # project website
    # license file
    # Application name ('InVEST'/'RIOS')
    # Installer title
    # Installer file name and output location
    # Installer log file save location
    # Installer icon location
    # Default installation location
    # Registry path
    # Start menu shortcut folder
    pass

def start_menu_links(options):
    formatted_string = ''
    # print them verbatim for now.
    for link_data in options:
        link_path = "${SMPATH}\\%s.lnk" % link_data['name']
        link_target = "$INSTDIR\\%s" % link_data['target']

        try:
            link_icon = link_data['icon']
        except KeyError:
            link_icon = ''

        formatted_string += "CreateShortCut \"%s\" \"%s\" \"%s\"\n" % (link_path,
                link_target, link_icon)

    return formatted_string

def uninstaller_registry_keys():
    formatted_string = """
    !define REG_KEY_FOLDER "${PUBLISHER} ${NAME} ${VERSION}"
    !define REGISTRY_PATH "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${REG_KEY_FOLDER}"
    !define UNINSTALL_PATH "${UNINSTALLER_PATH}"
    WriteRegStr HKLM "${REGISTRY_PATH}" "DisplayName"          "${PRODUCT_NAME} ${PRODUCT_VERSION}"
    WriteRegStr HKLM "${REGISTRY_PATH}" "UninstallString"      "$INSTDIR\${UNINSTALL_PATH}.exe"
    WriteRegStr HKLM "${REGISTRY_PATH}" "QuietUninstallString" "$INSTDIR\${UNINSTALL_PATH}.exe /S"
    WriteRegStr HKLM "${REGISTRY_PATH}" "InstallLocation"      "$INSTDIR"
    WriteRegStr HKLM "${REGISTRY_PATH}" "DisplayIcon"          "$INSTDIR\\${ICON}"
    WriteRegStr HKLM "${REGISTRY_PATH}" "Publisher"            "${PUBLISHER}"
    WriteRegStr HKLM "${REGISTRY_PATH}" "URLInfoAbout"         "${WEBSITE}"
    WriteRegStr HKLM "${REGISTRY_PATH}" "DisplayVersion"       "${VERSION}"
    WriteRegDWORD HKLM "${REGISTRY_PATH}" "NoModify" 1
    WriteRegDWORD HKLM "${REGISTRY_PATH}" "NoRepair" 1
    """

    return formatted_string

def save_log_file():
    return """
    ; Write the install log to a text file on disk.
    StrCpy $0 "$INSTDIR\install_log.txt"
    Push $0
    Call DumpLog
    """

def save_log_file_function():
    return """
Fuinction DumpLog
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
    """

def installer(installer_options):
    formatted_string = """
Section \"Install\" SEC01\n
  SetShellVarContext all
  SetOutPath "$INSTDIR"
  writeUninstaller "$INSTDIR\${UNINSTALL_PATH}.exe"

  ; Desired files are up one directory and in the given build folder.
  File /r "..\${BUILD_FOLDER}\*"
    """

    formatted_string += start_menu_links(installer_options['start_menu'])
    formatted_string += uninstaller_registry_keys()

    if installer_options['save_log']:
        formatted_string += save_log_file()

    formatted_string += """
SectionEnd
"""

    return formatted_string

def uninstaller():
    formatted_string = """
Section "uninstall"
    ; Need to enforce execution level as admin.  See
    ; nsis.sourceforge.net/Shortcuts_removal_fails_on_Windows_Vista
    SetShellVarContext all
    rmdir /r "$SMPROGRAMS\${PRODUCT_NAME} ${PRODUCT_VERSION}"

    ; Delete the installation directory on disk
    rmdir /r "$INSTDIR"

    ; Delete the entire registry key for this version of RIOS.
    DeleteRegKey HKLM "${REGISTRY_PATH}"
SectionEnd
"""
    return formatted_string

