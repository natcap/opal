;install_data_zips.nsi
;
;This file contains custom code included in the permitting installer.
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;CUSTOM CODE HERE

SetOutPath "$INSTDIR"
file ..\dist\tool_data.zip
CreateDirectory "$INSTDIR\data"
CreateDirectory "$INSTDIR\data\colombia_tool_data"
SetOutPath "$INSTDIR\data\colombia_tool_data\"
nsisunz::UnzipToLog "$INSTDIR\tool_data.zip" "."

;END OF CUSTOM UNZIPPING

