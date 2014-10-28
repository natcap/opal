import sys
import os
import argparse

import palisades
import palisades.i18n
from palisades import execution
from palisades import elements
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

if __name__ == '__main__':
    args_parser = argparse.ArgumentParser(
        description='Fire up the OPAL (or derivative) UI.')
    args_parser.add_argument('json_config',  metavar='json_config',
        help='JSON configuration file')
    args = args_parser.parse_args()

    print "Build data"
    for attr in palisades.build_data:
        print "%s: %s" % (attr, getattr(palisades, attr, False))

    if getattr(sys, 'frozen', False):
        # If we're in a pyinstaller build
        splash = os.path.join(os.path.dirname(sys.executable), 'splash.png')
    else:
        splash = os.path.join(os.getcwd(), 'windows_build', 'OPAL.png')
    print 'splash image: %s' % splash

    # use palisades function to locate the config in a couple of places.
    found_json = palisades.locate_config(args.json_config)

    # set up the palisades gui object and initialize the splash screen
    gui_app = palisades.gui.get_application()
    gui_app.show_splash(splash)
    gui_app.set_splash_message(palisades.SPLASH_MSG_CORE_APP)

    # create the core Application instance so that I can access its elements
    # for callbacks.
    ui = elements.Application(args.json_config,
        palisades.locate_dist_config()['lang'])
    ui._window.set_runner(MultilingualRunner)
    gui_app.set_splash_message(palisades.SPLASH_MSG_GUI)
    gui_app.add_window(ui._window)

    # start the interactive application
    gui_app.execute()

