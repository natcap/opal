"""Adept_core contains the core logic for the adept permitting tool."""

import logging

import invest_natcap

logging.basicConfig(format='%(asctime)s %(name)-18s %(levelname)-8s \
     %(message)s', level=logging.DEBUG, datefmt='%m/%d/%Y %H:%M:%S ')

LOGGER = logging.getLogger('adept')

def execute(args):
    """The main execution function for adept.
        args - a python dictionary containing the following elements:
           'project_footprint' - a URI to a shapefile of the project
                footprint
            'impact_type' - ???

        Returns nothing."""

    LOGGER.debug('   _____       .___             __   ')
    LOGGER.debug('  /  _  \\    __| _/____ _______/  |_ ')
    LOGGER.debug(' /  /_\\  \\  / __ |/ __ \\\\____ \\   __\\\\')
    LOGGER.debug('/    |    \\/ /_/ \\  ___/|  |_> >  |  ')
    LOGGER.debug('\\____|__  /\\____ |\\___  >   __/|__|  ')
    LOGGER.debug('        \\/      \\/    \\/|__|         ')
    LOGGER.debug('                                     ')

    LOGGER.debug('args %s' % args)