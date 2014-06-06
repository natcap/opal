!include "nsDialogs.nsh"

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

        ${NSD_CreateRadioButton} 5 50 100% 12u "Download during install"
        pop $CarbonDataDownload
        ${NSD_OnClick} $CarbonDataDownload CheckRadioButtonState

        ${NSD_CreateRadioButton} 5 70 100% 12u "Use a local file"
        pop $CarbonDataLocal
        ${NSD_OnClick} $CarbonDataLocal CheckRadioButtonState

        ${NSD_CreateLabel} 5 120 15% 12u "Select Zipfile"
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

var Dialog
var FileField
var FileLabel
var FileButton
var DataDownload
var DataLocal
!macro DataPage SectionHandle Title Label
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

    ${NSD_CreateRadioButton} 5 50 100% 12u "Download during install"
    pop $DataDownload
;    strcpy $DataDownload $0
    ${NSD_OnClick} $DataDownload CheckRadioButtonState

    ${NSD_CreateRadioButton} 5 70 100% 12u "Use a local file"
    pop $DataLocal
;    strcpy $DataLocal $0
    ${NSD_OnClick} $DataLocal CheckRadioButtonState
    ${NSD_SetState} $DataLocal 1

    ${NSD_CreateLabel} 5 120 15% 12u "Select Zipfile"
    pop $FileLabel
;    strcpy $FileLabel $0
;    EnableWindow $FileLabel 0

    ${NSD_CreateFileRequest} 100 120 60% 12u ""
    pop $FileField
;    strcpy $FileField $0
;    EnableWindow $FileField 0

    ${NSD_CreateBrowseButton} 400 120 10% 12u "file"
    pop $FileButton
;    strcpy $FileButton $0
    ${NSD_OnClick} $FileButton GetZipFile
;    EnableWindow $FileButton 0

    nsDialogs::Show
!macroEnd        

Function GetZipFile
    nsDialogs::SelectFileDialog "open" "" "Zipfiles *.zip"
    pop $0
    ${GetFileExt} $0 $1
    ${If} "$1" != "zip"
        MessageBox MB_OK "File must be a zipfile"
        Abord
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

!macro DataPageLeave FileVar
    ${NSD_GetText} $FileField ${FileVar}
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
