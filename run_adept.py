import palisades
from palisades import elements

ui = elements.Application('adept.json')
gui = palisades.gui.build(ui._window)
gui.execute()
