grep \"en\" $1 | grep --color -o \:\ \"[^\"]*\", | sed s/[\":,$]//g
