
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

    ${NSD_CreateRadioButton} 5 70 100% 12u "Use a local file"
    pop $CarbonDataLocal

    ${NSD_CreateLabel} 5 120 15% 12u "Select Zipfile"
    pop $CarbonFileLabel

    ${NSD_CreateFileRequest} 100 120 60% 12u "label"
    pop $CarbonFile

    ${NSD_CreateBrowseButton} 400 120 10% 12u "file"
    pop $CarbonFileButton
    ${NSD_OnClick} $CarbonFileButton GetZipFile

    nsDialogs::Show
    
FunctionEnd

var ZipURI
Function GetZipFile
    pop $1
    nsDialogs::SelectFileDialog "open" "" "Zipfiles *.zip"
    pop $ZipURI
    ${NSD_SetText} $CarbonFile $ZipURI
FunctionEnd
