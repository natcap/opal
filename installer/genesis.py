"""Genesis - NSIS generator"""

import json
import sys
import argparse
import os
import codecs
from types import DictType

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
    rmdir /r "${START_MENU_FOLDER}"

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

class EncodingFound(Exception): pass

def build_installer_script(config_file_uri, out_file_uri):
    config_dict = None
    try:
        for encoding in ['utf-8', 'latin-1']:
            try:
                new_file = codecs.open(out_file_uri, 'w', encoding)
                config_dict = json.load(open(config_file_uri), encoding)
                raise EncodingFound  # if this succeeds, break out of the loop.
            except UnicodeDecodeError:
                print 'Encoding %s failed.  Skipping.' % encoding
    except EncodingFound:
        print 'Found an encoding: %s' % encoding

    if config_dict is None:
        raise RuntimeError("Can't understand the encoding!")

    # check for default values before writing the script.
    sanitized_config = check_defaults(config_dict)

    new_file.write(local_variables(sanitized_config))
    try:
        custom_pages = sanitized_config['installer']['custom_pages']
    except KeyError:
        custom_pages = []

    new_file.write(general_settings(custom_pages))

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

def installer_pages(custom_pages):
    pages_string = """
; MUI installer pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE ${LICENSE_FILE}
!insertmacro MUI_PAGE_COMPONENTS
"""
    for custom_page in custom_pages:
        custom_string = 'Page Custom %s %s\n' % (custom_page['enter_funcname'],
            custom_page['leave_funcname'])
        pages_string += custom_string

    pages_string += """
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

def general_settings(custom_pages):
    general_settings = """
; Set the compression size and type.
SetCompressor /FINAL /SOLID lzma
SetCompressorDictSize 64

; MUI 1.67 compatible macro settings------
; Installer settings.
!include "MUI.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"
!include "FileFunc.nsh"
!include "genesis.nsh"
"""

    general_settings += installer_pages(custom_pages)
    general_settings += uninstaller_pages()
    general_settings += """
Name "${INTERNAL_NAME} ${VERSION}"
OutFile "${INSTALLER_FILENAME}"
InstallDir "${DEFAULT_INSTALL_DIR}"
ShowInstDetails show
"""
    return general_settings


def section(options):
    # ASSUMING ONLY ONE LEVEL OF OPTIONS
    compact_section_name = options['name'].replace(' ', '')
    section_type = options['action']['type']
    if section_type.startswith('unzip'):
        file_varname = "%sFile" % os.path.splitext(
            os.path.basename(options['action']['zipfile'].replace('\\', '/')))[0]
        strings = ['var %s' % file_varname]
    else:
        strings = []

    strings += [
        'Section \"%s\" %s' % (options['name'], compact_section_name)
    ]

    unzip_page_funcs = False
    try:
        file_size = int(options['size'])
    except ValueError:
        # when options['size'] is a path
        try:
            # file_size is in kb.
            file_size = os.path.getsize(options['size'].replace('\\', '/')) >> 10
        except (OSError, TypeError):
            # Size MUST be in options, so DO NOT catch a keyError here.
            # OSError when options['size'] is a string but does not exist on disk
            # TypeError when options['size'] is not a string
            file_size = None

    if section_type.startswith('unzip'):
        if file_size is None:
            # get filesize in kb
            file_size = os.path.getsize(
                options['action']['zipfile'].replace('\\', '/')) >> 10
        strings.append(
            'AddSize \"%s\"' % (file_size)
        )

        if section_type == 'unzipSelect':
            strings.append('!insertmacro DownloadIfEmpty "$%s" "%s" "%s" "%s"' % (
                file_varname, options['action']['target_dir'],
                options['action']['downloadURL'],
                os.path.basename(options['action']['zipfile'].replace('\\',
                    '/'))))

            unzip_page_funcs = True
        else:
            zipfile_uri = options['action']['zipfile']
            strings += [
                'CreateDirectory \"%s\"' % options['action']['target_dir'],
                'SetOutPath \"%s\"' % options['action']['target_dir'],
                'nsisunz::UnzipToLog \"%s\" \".\"' % zipfile_uri,
                'StrCpy $0 "$INSTDIR\\%s.log' % zipfile_uri,
                'Push $0',
                'Call DumpLog',
            ]
    else:
        strings.append('AddSize \"%s\"' % file_size)

    strings.append('SectionEnd\n')

    def _lang_strings(varname, language_config):
        """language config should look like:
            {
                "english": "some en string",
                "spanish": "some es string"
            }"""
        lang_strings = []
        for lang_name, lang_string in language_config.iteritems():
            lang_string = 'LangString %s ${LANG_%s} "%s"' % (varname,
                lang_name.upper(), lang_string)
            lang_strings.append(lang_string)
        return '\n'.join(lang_strings)

    if unzip_page_funcs:
        label_name = options['name'].replace(' ', '_').replace('-', '_').upper()
        func_name = options['name'].replace(' ', '').replace('-', '') + 'Function'
        strings += [
            '',
            _lang_strings(label_name + '_LABEL', options['label']),
            'Function %s' % func_name,
            '    !insertmacro DataPage ${%s} "" "$(%s)"' %
                (compact_section_name, label_name + '_LABEL'),
            'FunctionEnd',
            ''
            'Function %s' % func_name + 'Leave',
            '    !insertmacro DataPageLeave $%s' % file_varname,
            'FunctionEnd\n\n'
            ''
        ]

    return '\n'.join(strings)

def local_variables(options):
    custom_vars = []
    for var_name, var_value in options['variables'].iteritems():
        custom_vars.append('!define %s "%s"' % (var_name, var_value))

    # NSIS variables for custom functionality that might be used later on.
    for var_name in ['ZipFileURI']:
        custom_vars.append('Var %s' % var_name)

    strings = [
        '',
        '',
        '; GENERAL APPLICATION INFORMATION VARIABLES',
        # TODO: add NAME, VERSION, architecture based on the json config
        '!define INTERNAL_NAME "%s"' % options['general']['name'],
        '!define INTERNAL_VERSION "%s"' % options['general']['version'],
        '!define INTERNAL_ARCHITECTURE "%s"' % options['general']['architecture'],

        '!define PUBLISHER "%s"' % options['general']['publisher'],
        '!define WEBSITE "%s"' % options['general']['website'],
        '',
        '',
        '; INSTALLER INFORMATION',
        '!define INSTALLER_TITLE "%s"' % options['installer']['title'],
        '!define BUILD_FOLDER "%s"' % options['general']['build_folder'],
        '!define INSTALLER_FILENAME "%s"' % options['installer']['filename'],
        '!define INSTALLER_LOGFILE "%s"' % options['installer']['install_log'],
        '!define INSTALLER_ICON "%s"' % options['installer']['icon'],
        '!define DEFAULT_INSTALL_DIR "%s"' % options['installer']['install_dir'],
        '!define LICENSE_FILE "%s"' % options['installer']['license'],
        '!define START_MENU_FOLDER "$SMPROGRAMS\\${INTERNAL_NAME} ${INTERNAL_VERSION}"',
        '',
        '',
        '; UNINSTALLER INFORMATION',
        '!define UNINSTALLER_FILENAME "%s"' % options['uninstaller']['filename'],
        '!define REGISTRY_PATH "%s"' % (
            'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\'
            '${PUBLISHER} ${INTERNAL_NAME} ${INTERNAL_VERSION}'),
        '',
        '']

    formatted_string = '\n'.join(custom_vars)
    formatted_string += '\n'.join(strings)
    return formatted_string

def _lang_strings(varname, language_config):
    """language config should look like:
        {
            "english": "some en string",
            "spanish": "some es string"
        }"""
    lang_strings = []
    for lang_name, lang_string in language_config.iteritems():
        lang_string = 'LangString %s ${LANG_%s} "%s"' % (varname,
            lang_name.upper(), lang_string)
        lang_strings.append(lang_string)
    return '\n'.join(lang_strings)

def start_menu_links(options):
    formatted_string = ''
    languages = ''
    formatted_string += "CreateDirectory \"${START_MENU_FOLDER}\"\n"
    # print them verbatim for now.
    for link_data in options:
        if type(link_data['name']) is DictType:
            varname = link_data['name']['english'].replace(' ', '').upper() + '_LANG'
            languages += _lang_strings(varname, link_data['name']) + '\n'
            link_name = '$(%s)' % varname
        else:
            # no language dictionary provided, assume string.
            link_name = link_data['name']

        link_path = "${START_MENU_FOLDER}\\%s.lnk" % link_name
        link_target = "$INSTDIR\\%s" % link_data['target']
        try:
            link_icon = link_data['icon']
        except KeyError:
            link_icon = ''

        formatted_string += "CreateShortCut \"%s\" \"%s\" \"%s\"\n" % (link_path,
                link_target, link_icon)

    return (formatted_string, languages)

def installer(installer_options):
    formatted_string = """
Section \"Core scripts and data\" SEC01\n
  SetShellVarContext all
  SetOutPath "$INSTDIR"
  writeUninstaller "$INSTDIR\${UNINSTALLER_FILENAME}.exe"

  ; Desired files are up one directory and in the given build folder.
  File /r "${BUILD_FOLDER}\*"
    """

    try:
        if installer_options['required']:
            formatted_string += 'SectionIn RO\n'
    except KeyError:
        pass

    try:
        formatted_string += 'AddSize \"%s\"\n' % installer_options['size']
    except KeyError:
        pass

    links, languages = start_menu_links(installer_options['start_menu'])
    formatted_string += links
    formatted_string = languages + formatted_string  # prepend section with langs
    formatted_string += UNINSTALLER_REG_KEYS

    if 'extra_files' in installer_options:
        for extra_file in installer_options['extra_files']:
            formatted_string += '    File %s\n' % extra_file

    if 'post_install' in installer_options:
        formatted_string += open(installer_options['post_install'], 'r').read()

    if installer_options['save_log']:
        formatted_string += SAVE_LOG_FILE

    formatted_string += """
SectionEnd

"""
    try:
        for section_config in installer_options['sections']:
            formatted_string += section(section_config)
    except KeyError:
        raise


    return formatted_string

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', dest='config_uri',
        help='JSON file with input arguments', type=unicode, metavar='',
        required=True)
    parser.add_argument('-o', '--output', dest='output_uri',
        help='URI of output filepath', type=unicode, metavar='', required=True)

    args = parser.parse_args()
    config_uri = args.config_uri
    output_uri = args.output_uri
    build_installer_script(config_uri, output_uri)
