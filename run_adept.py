import sys
import os

import palisades
import palisades.i18n
from palisades import execution
import adept.i18n

class MultilingualRunner(execution.PythonRunner):
    def start(self):
        """Start the execution.
        Overridden here to take the language of the palisades UI and set the
        adept package language to the same language code."""
        palisades_lang = palisades.i18n.current_lang()
        print 'setting adept lang to %s' % palisades_lang
        adept.i18n.language.set(palisades_lang)
        execution.PythonRunner.start(self)

print "Build data"
for attr in palisades.build_data:
    print "%s: %s" % (attr, getattr(palisades, attr, False))

if getattr(sys, 'frozen', False):
    # If we're in a pyinstaller build
    splash = os.path.join(os.path.dirname(sys.executable), 'splash.png')
else:
    splash = os.path.join(os.getcwd(), 'windows_build', 'OPAL.png')
print 'splash image: %s' % splash

palisades.launch('adept.json', splash, MultilingualRunner)
