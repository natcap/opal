import palisades
from palisades import elements
import adept
import os
import sys

os.environ['MATPLOTLIBDATA'] = os.path.join(os.path.dirname(sys.executable),
'mpl-data')

if adept.is_frozen():
    adept_uri = os.path.join(adept.get_frozen_dir(), 'adept.json')
else:
    adept_uri = 'adept.json'
ui = elements.Application(adept_uri)
gui = palisades.gui.build(ui._window)
gui.execute()
