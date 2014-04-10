import palisades
from palisades import elements
import adept
import os
import sys

if adept.is_frozen():
    adept_uri = os.path.join(adept.get_frozen_dir(), 'adept.json')
    #adept_uri = os.path.join(sys._MEIPASS, 'adept.json')
else:
    adept_uri = 'adept.json'
ui = elements.Application(adept_uri)
gui = palisades.gui.build(ui._window)
gui.execute()
