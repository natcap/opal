import sys
import os
import argparse
import logging

import palisades
import palisades.i18n
from palisades import execution
from palisades import elements
import adept.i18n

PALISADES_LOGGER = logging.getLogger('palisades')
PALISADES_LOGGER.setLevel(logging.INFO)

class MultilingualRunner(execution.PythonRunner):
    def start(self):
        """Start the execution.
        Overridden here to take the language of the palisades UI and set the
        adept package language to the same language code."""
        palisades_lang = palisades.i18n.current_lang()
        print 'setting adept lang to %s' % palisades_lang
        adept.i18n.language.set(palisades_lang)
        execution.PythonRunner.start(self)

def setup_opal_callbacks(ui_obj):
    servicesheds_elem = ui_obj.find_element('servicesheds_map')
    sediment_cb_elem = ui_obj.find_element('do_sediment')
    nutrient_cb_elem = ui_obj.find_element('do_nutrient')
    custom_cb_elem = ui_obj.find_element('do_custom')
    custom_ssheds_elem = ui_obj.find_element('custom_es_input_type')

    # callback should be called when the collapsible container's collapsed
    # signal is triggered.
    def _require_servicesheds(value=None):
        print 'require_servicesheds value=%s' % value
        sed_is_checked = sediment_cb_elem.value()
        nut_is_checked = nutrient_cb_elem.value()
        custom_is_checked = custom_cb_elem.value()

        require_ssheds = False
        if sed_is_checked or nut_is_checked:
            require_ssheds = True
        elif custom_is_checked:
            ssheds_type = custom_ssheds_elem.value()
            require_ssheds = ssheds_type == 'hydrological'

        servicesheds_elem.set_conditionally_required(require_ssheds)
        servicesheds_elem.validate()

        print 'is required: %s' % servicesheds_elem.is_required()
        print 'is cond. required: %s' % servicesheds_elem._conditionally_required
        print 'sheds value: %s' % custom_ssheds_elem.value()

    sediment_cb_elem.toggled.register(_require_servicesheds)
    nutrient_cb_elem.toggled.register(_require_servicesheds)
    custom_cb_elem.toggled.register(_require_servicesheds)
    custom_ssheds_elem.value_changed.register(_require_servicesheds)
    _require_servicesheds()  # initialize the requirement state
    servicesheds_elem.validate()

if __name__ == '__main__':
    print "Build data"
    for attr in palisades.build_data:
        print "%s: %s" % (attr, getattr(palisades, attr, False))

    if getattr(sys, 'frozen', False):
        # If we're in a pyinstaller build
        splash = os.path.join(os.path.dirname(sys.executable), 'splash.png')
        json_config = sys.argv[0]
    else:
        splash = os.path.join(os.getcwd(), 'windows_build', 'OPAL.png')
        args_parser = argparse.ArgumentParser(
            description='Fire up the OPAL (or derivative) UI.')
        args_parser.add_argument('json_config',  metavar='json_config',
            help='JSON configuration file')
        args = args_parser.parse_args()
        json_config = args.json_config
    print 'splash image: %s' % splash

    # write this information, just in case.
    debug_file = open(os.path.expanduser('~/debug.txt'), 'w')
    debug_file.write(json_config)
    debug_file.close()

    # use palisades function to locate the config in a couple of places.
    found_json = palisades.locate_config(json_config)
    print 'JSON URI: %s' % found_json

    # set up the palisades gui object and initialize the splash screen
    gui_app = palisades.gui.get_application()
    gui_app.show_splash(splash)
    gui_app.set_splash_message(palisades.SPLASH_MSG_CORE_APP)

    # create the core Application instance so that I can access its elements
    # for callbacks.
    ui = elements.Application(found_json,
        palisades.locate_dist_config()['lang'])
    if os.path.basename(found_json) == 'opal.json':
        setup_opal_callbacks(ui._window)

    ui._window.set_runner(MultilingualRunner)
    gui_app.set_splash_message(palisades.SPLASH_MSG_GUI)
    gui_app.add_window(ui._window)

    # start the interactive application
    gui_app.execute()

