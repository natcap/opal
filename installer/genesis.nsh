
var CarbonDialog
var CarbonLabel
var CarbonDataDownload
var CarbonDataLocal
var CarbonFile
var CarbonFileLabel
var CarbonFileButton
Function CarbonSMDataPageNSD
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
