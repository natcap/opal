import palisades
from palisades import elements

ui = elements.Application('sediment_sm.json')
gui = palisades.gui.build(ui._window)
gui.execute()
