import sys
import os
import argparse
import logging

from PyQt4 import QtGui

import palisades
import palisades.i18n
from palisades import execution
from palisades import elements
import adept.i18n

# capture palisades logging and only display INFO or higher
PALISADES_LOGGER = logging.getLogger('palisades')
PALISADES_LOGGER.setLevel(logging.INFO)

LOGGER = logging.getLogger('_opal_launch')

class MultilingualRunner(execution.PythonRunner):
    def start(self):
        """Start the execution.
        Overridden here to take the language of the palisades UI and set the
        adept package language to the same language code."""
        palisades_lang = palisades.i18n.current_lang()
        print 'setting adept lang to %s' % palisades_lang
        adept.i18n.language.set(palisades_lang)
        execution.PythonRunner.start(self)

class OPALInfoDialog(QtGui.QDialog):
    def __init__(self):
        QtGui.QDialog.__init__(self)

        self.setLayout(QtGui.QVBoxLayout())
        self.opal_version = QtGui.QLabel(adept.__version__)
        self.palisades_version = QtGui.QLabel(palisades.__version__)
        self.layout().addWidget(self.opal_version)
        self.layout().addWidget(self.palisades_version)

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

def main(json_config=None):
    # add logging handler so this stuff is written to disk
    if json_config is None:
        logfile_filename = 'debug_unknown'
    else:
        logfile_filename = 'debug_%s' % json_config.replace('.json', '')
    logfile_dirname = os.path.join('C:', 'Users', 'jadoug06')
    logfile_path = os.path.join(logfile_dirname, logfile_filename +
        '.txt')
    debug_handler = logging.FileHandler(logfile_path, 'w', encoding='utf-8')
    LOGGER.addHandler(debug_handler)
    PALISADES_LOGGER.addHandler(debug_handler)

    LOGGER.debug("Palisads build data")
    for attr in palisades.build_data:
        LOGGER.debug("%s: %s", attr, getattr(palisades, attr, False))

    if getattr(sys, 'frozen', False):
        # If we're in a pyinstaller build
        exe_dir = os.path.dirname(sys.executable)
        splash = os.path.join(exe_dir, 'splash.png')
        if json_config is None:
            json_config = sys.argv[1]  # the first program argument
        app_icon = os.path.join(exe_dir, 'opal-logo-small.png')
        opal_logo = os.path.join(exe_dir, 'opal-logo-small.png')
    else:
        splash = os.path.join(os.getcwd(), 'windows_build', 'OPAL.png')
        args_parser = argparse.ArgumentParser(
            description='Fire up the OPAL (or derivative) UI.')
        args_parser.add_argument('json_config',  metavar='json_config',
            help='JSON configuration file')
        args = args_parser.parse_args()
        if json_config is None:
            json_config = args.json_config
        app_icon = os.path.join(os.getcwd(), 'windows_build',
            'opal-logo-small.png')
        opal_logo = os.path.join(os.getcwd(), 'installer', 'opal_images',
            'opal-logo-small.png')
    LOGGER.debug('splash image: %s', splash)

    # use palisades function to locate the config in a couple of places.
    found_json = palisades.locate_config(json_config)
    LOGGER.debug('JSON URI: %s', found_json)

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

    # set the application icon
    # TODO: make an easier way to set the window icon.
    form_window = gui_app.windows[0].window
    form_window.setWindowIcon(QtGui.QIcon(app_icon))

    # set the stuff of the infoDialog.
    form_window.app_info_dialog.set_title('About OPAL')
    form_window.app_info_dialog.set_messages = 'Version!'
    form_window.app_info_dialog.set_icon(opal_logo, scale=True)

    #form_window.menu_bar.addMenu(help_menu)
    form_window.layout().setMenuBar(form_window.menu_bar)

    # start the interactive application
    gui_app.execute()

if __name__ == '__main__':
    main()

