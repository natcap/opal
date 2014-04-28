;install_data_zips.nsi
;
;This file contains custom code included in the permitting installer.
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;CUSTOM CODE HERE

SetOutPath "$INSTDIR"

Section "Static Data"
    AddSize "10000000"

    File ..\dist\*.zip
    CreateDirectory "$INSTDIR\data"
    CreateDirectory "$INSTDIR\data\colombia_static_data"
    SetOutPath "$INSTDIR\data\colombia_static_data\"
    nsisunz::UnzipToLog "$INSTDIR\static_data.zip" "."
SectionEnd

CreateDirectory "$INSTDIR\data\colombia_tool_data"
SetOutPath "$INSTDIR\data\colombia_tool_data\"
nsisunz::UnzipToLog "$INSTDIR\tool_data.zip" "."

;END OF CUSTOM UNZIPPING
    
