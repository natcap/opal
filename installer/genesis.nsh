!include "nsDialogs.nsh"

LangString DOWNLOAD_DURING_INSTALL ${LANG_ENGLISH} "Download during install"
LangString DOWNLOAD_DURING_INSTALL ${LANG_SPANISH} "Descargar durante la instalación"
LangString USE_LOCAL_FILE ${LANG_ENGLISH} "Use a local file"
LangString USE_LOCAL_FILE ${LANG_SPANISH} "Utilice un archivo local"
LangString SELECT_ZIPFILE ${LANG_ENGLISH} "Select zipfile"
LangString SELECT_ZIPFILE ${LANG_SPANISH} "Seleccionar archivo de zip"
LangString FILE_BUTTON ${LANG_ENGLISH} "Select"
LangString FILE_BUTTON ${LANG_SPANISH} "Seleccionar"

!macro locateDataZip Title Label
    Page custom CarbonSMDataPageNSD1

    var CarbonDialog
    var CarbonLabel
    var CarbonDataDownload
    var CarbonDataLocal
    var CarbonFile
    var CarbonFileLabel
    var CarbonFileButton
    Function CarbonSMDataPageNSD1
        SectionGetFlags ${SectionCarbonStaticData} $R0
        IntOp $R0 $R0 & ${SF_SELECTED}
        IntCmp $R0 ${SF_SELECTED} show
        Abort

        show:
        nsDialogs::Create 1018
        pop $CarbonDialog

        ${NSD_CreateLabel} 5 5 100% 24u "Select a zipfile containing default carbon static data.  This can be downloaded from http://ncp-dev.stanford.edu/~dataportal/nightly-build/adept/data/carbon.zip."
        pop $CarbonLabel

        ${NSD_CreateRadioButton} 5 50 100% 12u "$(DOWNLOAD_DURING_INSTALL)"
        pop $CarbonDataDownload
        ${NSD_OnClick} $CarbonDataDownload CheckRadioButtonState

        ${NSD_CreateRadioButton} 5 70 100% 12u "$(USE_LOCAL_FILE)"
        pop $CarbonDataLocal
        ${NSD_OnClick} $CarbonDataLocal CheckRadioButtonState

        ${NSD_CreateLabel} 5 120 15% 12u "$(SELECT_ZIPFILE)"
        pop $CarbonFileLabel
        EnableWindow $CarbonFileLabel 0

        ${NSD_CreateFileRequest} 100 120 60% 12u "label"
        pop $CarbonFile
        EnableWindow $CarbonFile 0

        ${NSD_CreateBrowseButton} 400 120 10% 12u "file"
        pop $CarbonFileButton
        ${NSD_OnClick} $CarbonFileButton GetZipFile
        EnableWindow $CarbonFileButton 0

        nsDialogs::Show
        
    FunctionEnd

    var ZipURI
    Function GetZipFile
        pop $1
        nsDialogs::SelectFileDialog "open" "" "Zipfiles *.zip"
        pop $ZipURI
        ${NSD_SetText} $CarbonFile $ZipURI
    FunctionEnd

    var isChecked
    var enableState
    Function CheckRadioButtonState
        # check the state of the local download radio button.
        ${NSD_GetState} $CarbonDataLocal $isChecked
        ${If} $isChecked == 1
            strcpy $enableState 1
        ${Else}
            strcpy $enableState 0
        ${EndIf}
        EnableWindow $CarbonFileButton $enableState
        EnableWindow $CarbonFileLabel $enableState
        EnableWindow $CarbonFile $enableState
    FunctionEnd
!macroend

; Taken from http://nsis.sourceforge.net/StrRep
!define StrRep "!insertmacro StrRep"
!macro StrRep output string old new
    Push `${string}`
    Push `${old}`
    Push `${new}`
    !ifdef __UNINSTALL__
        Call un.StrRep
    !else
        Call StrRep
    !endif
    Pop ${output}
!macroend
 
!macro Func_StrRep un
    Function ${un}StrRep
        Exch $R2 ;new
        Exch 1
        Exch $R1 ;old
        Exch 2
        Exch $R0 ;string
        Push $R3
        Push $R4
        Push $R5
        Push $R6
        Push $R7
        Push $R8
        Push $R9
 
        StrCpy $R3 0
        StrLen $R4 $R1
        StrLen $R6 $R0
        StrLen $R9 $R2
        loop:
            StrCpy $R5 $R0 $R4 $R3
            StrCmp $R5 $R1 found
            StrCmp $R3 $R6 done
            IntOp $R3 $R3 + 1 ;move offset by 1 to check the next character
            Goto loop
        found:
            StrCpy $R5 $R0 $R3
            IntOp $R8 $R3 + $R4
            StrCpy $R7 $R0 "" $R8
            StrCpy $R0 $R5$R2$R7
            StrLen $R6 $R0
            IntOp $R3 $R3 + $R9 ;move offset by length of the replacement string
            Goto loop
        done:
 
        Pop $R9
        Pop $R8
        Pop $R7
        Pop $R6
        Pop $R5
        Pop $R4
        Pop $R3
        Push $R0
        Push $R1
        Pop $R0
        Pop $R1
        Pop $R0
        Pop $R2
        Exch $R1
    FunctionEnd
!macroend
!insertmacro Func_StrRep ""
!insertmacro Func_StrRep "un."


var Dialog
var FileField
var FileLabel
var FileButton
var DataDownload
var DataLocal
!macro DataPage SectionHandle Title Label FileVar UseLocalVar
    SectionGetFlags ${SectionHandle} $R0
    IntOp $R0 $R0 & ${SF_SELECTED}
    IntCmp $R0 ${SF_SELECTED} show
    Abort

    show:
    nsDialogs::Create 1018
    pop $Dialog
;    strcpy $Dialog $0

    ${NSD_CreateLabel} 5 5 100% 24u "${Label}"
    pop $FileLabel
;    strcpy $FileLabel $0

    ${NSD_CreateRadioButton} 5 50 100% 12u "$(DOWNLOAD_DURING_INSTALL)"
    pop $DataDownload
;    strcpy $DataDownload $0
    ${NSD_OnClick} $DataDownload CheckRadioButtonState

    ${NSD_CreateRadioButton} 5 70 100% 12u "$(USE_LOCAL_FILE)"
    pop $DataLocal
;    strcpy $DataLocal $0
    ${NSD_OnClick} $DataLocal CheckRadioButtonState

    ${NSD_CreateLabel} 5 120 20% 24u "$(SELECT_ZIPFILE)"
    pop $FileLabel
;    strcpy $FileLabel $0
;    EnableWindow $FileLabel 0

    ${NSD_CreateFileRequest} 100 120 60% 12u ""
    pop $FileField
    ${NSD_SetText} $FileField ${FileVar}
;    strcpy $FileField $0
;    EnableWindow $FileField 0

    ${NSD_CreateBrowseButton} 400 120 20% 12u "$(FILE_BUTTON)"
    pop $FileButton
;    strcpy $FileButton $0
    ${NSD_OnClick} $FileButton GetZipFile
;    EnableWindow $FileButton 0


    ; Set the default enable state based on the previous radio button state,
    ; if it exists.
    ; NOTE: if $UseLocalVar has not yet been used, its value is ""
    ${If} ${UseLocalVar} == 0
        ${NSD_SetState} $DataLocal 0
        ${NSD_SetState} $DataDownload 1
    ${Else}
        ${NSD_SetState} $DataLocal 1
        ${NSD_SetState} $DataDownload 0
    ${EndIf}
    call CheckRadioButtonState  ; set the enabled state

    nsDialogs::Show
!macroEnd        

Function GetZipFile
    nsDialogs::SelectFileDialog "open" "" "Zipfiles *.zip"
    pop $0
    ${GetFileExt} $0 $1
    ${If} "$1" != "zip"
        MessageBox MB_OK "$(MUST_BE_ZIPFILE)"
        Abort
    ${EndIf}

    ${NSD_SetText} $FileField $0
FunctionEnd

Function CheckRadioButtonState
    # check the state of the local download radio button.
    ${NSD_GetState} $DataLocal $0
    ${If} $0 == 1
        strcpy $1 1
    ${Else}
        strcpy $1 0
    ${EndIf}
    EnableWindow $FileButton $1
    EnableWindow $FileLabel $1
    EnableWindow $FileField $1
FunctionEnd

LangString MUST_PROVIDE_ZIPFILE ${LANG_ENGLISH} "You must provide a zipfile"
LangString MUST_PROVIDE_ZIPFILE ${LANG_SPANISH} "Usted debe proporcionar un archivo zip"
LangString SELECT_DIFFERENT_FILE ${LANG_ENGLISH} "Could not find the file '__FILE__'.  Please select a different file"
LangString SELECT_DIFFERENT_FILE ${LANG_SPANISH} "No se pudo encontrar el archivo '__FILE__'.  Por favor, seleccione un archivo diferente"
LangString MUST_BE_ZIPFILE ${LANG_ENGLISH} "File must be a zipfile (*.zip)"
LangString MUST_BE_ZIPFILE ${LANG_SPANISH} "El archivo debe ser un archivo zip (*.zip)"
!macro DataPageLeave FileVar UseLocal
    ${NSD_GetText} $FileField ${FileVar}
    ${NSD_GetState} $DataLocal ${UseLocal}

    ; get the enabled state of the local download radio button to determine
    ; If we need to validate the filename of the archive provided.
    ${NSD_GetState} $DataLocal $0
    ${If} $0 == 1
        ${If} "${FileVar}" == "" 
            MessageBox MB_OK "$(MUST_PROVIDE_ZIPFILE)"
            Abort
        ${ElseIfNot} ${FileExists} ${FileVar}
            ${StrRep} $0 "$(SELECT_DIFFERENT_FILE)" "__FILE__" "${FileVar}"
            MessageBox MB_OK "$0"
        ${Else}
            ${GetFileExt} ${FileVar} $1
            ${If} "$1" != "zip"
                MessageBox MB_OK "$(MUST_BE_ZIPFILE)"
            ${EndIf}
        ${EndIf}
    ${EndIf}

!macroend

!macro DownloadIfEmpty Path DestDir DownloadURL LocalFileName
    CreateDirectory "${DestDir}"
    SetOutPath "${DestDir}"
;    MessageBox MB_OK "${Path}"

    ${If} ${Path} == ""  ; if no path defined
        NSISdl::download ${DownloadURL} "${LocalFileName}"
        ; $0 contains the local file name
;        MessageBox MB_OK "$LocalFileName"
        nsisunz::UnzipToLog "${LocalFileName}" "."
    ${Else}
        nsisunz::UnzipToLog ${Path} "."
    ${EndIf}
!macroend
