import sys
import os
import multiprocessing

# import adept and static_maps here so that we absolutely guarantee that we're
# going to have access to these packages when palisades needs to do its dynamic
# imports.
import adept
from adept import static_maps

multiprocessing.freeze_support()

os.environ['MATPLOTLIBDATA'] = os.path.join(sys._MEIPASS, 'mpl-data')
