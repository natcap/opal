grep \"en\" adept.json | grep --color -o \:\ \"[^\"]*\", | sed s/[\":,$]//g
