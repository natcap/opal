"""Genesis - NSIS generator"""

import demjson  # using for js compaibility -- comments in JSON files.
import sys

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

def uninstaller_registry_keys(uninstall_options):
    formatted_string = """
    !define REG_KEY_FOLDER "${PUBLISHER} ${NAME} ${VERSION}"
    !define REGISTRY_PATH "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${REG_KEY_FOLDER}"
    !define UNINSTALL_PATH "%s"
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
    """ % (uninstall_options['filename'])

    return formatted_string


