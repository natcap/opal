import palisades
import sys
import os

print "Build data"
for attr in palisades.build_data:
    print "%s: %s" % (attr, getattr(palisades, attr, False))

if getattr(sys, 'frozen', False):
    # If we're in a pyinstaller build
    splash = os.path.join(os.path.dirname(sys.executable), 'splash.png')
else:
    splash = os.path.join(os.getcwd(), 'windows_build', 'OPAL.png')
print 'splash image: %s' % splash

palisades.launch('adept.json', splash)
