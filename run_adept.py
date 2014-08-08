import palisades
import sys
import os

print "Build data"
for attr in palisades.build_data:
    print "%s: %s" % (attr, getattr(palisades, attr, False))

if getattr(sys, 'frozen', False):
    # If we're in a pyinstaller build
    splash = os.path.join(os.path.dirname(sys.executable), 'splash.jpg')
else:
    splash = os.path.join('windows_build', 'OPAL.jpg')

palisades.launch('adept.json', splash)
