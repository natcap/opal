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
from adept import versioning

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

    # now, set up the OPAL future scenario validation requirements.
    future_type_elem = ui_obj.find_element('offset_type')

    def _fut_filename(model, scenario, suffix=''):
        if suffix != '':
            suffix = '_%s' % suffix

        if scenario == 'Protection':
            scenario = 'protect'
        else:
            scenario = 'restore'

        return '%s_%s%s.tif' % (model, scenario, suffix)

    def _remove_future_rasters(raster_list):
        """Take a list of raster filenames and remove any rasters in it that
        are known to represent future scenarios."""
        new_list = []
        for raster in raster_list:
            if 'protect' in raster or 'restore' in raster:
                continue
            new_list.append(raster)
        return new_list

    def _setup_future_validation(model_name, target_elem, include_pts=True):
        """Set up a callback function tailored to work with a particular static
        model name and static map element.  This callback will require
        future scenario rasters depending on the value of the future scenario
        dropdown.

        Returns a function pointer that will work as a callback."""
        def _setup_fut_validation(value=None, validate=True):
            """Callback for setting up future validation for a static map input
            element, where future scenarios are required by validation, but the
            required future scenario is dependent on the value of the future
            scenario type.

            Returns nothing, but has a side effect of affecting the target
            static map folder element's validation dictionary."""
            future_type = future_type_elem.value()
            expected_fut_raster = _fut_filename(model_name, future_type,
                'static_map')
            cur_raster_list = target_elem.config['validateAs']['contains']
            new_raster_list = _remove_future_rasters(cur_raster_list)
            new_raster_list.append(expected_fut_raster)

            if include_pts is True:
                pts_raster = _fut_filename(model_name, future_type, 'pts')
                new_raster_list.append(pts_raster)

            target_elem.config['validateAs']['contains'] = new_raster_list

            if validate is True:
                target_elem.validate()

        # initialize the input element's future validation without actually
        # triggering validation (not until user input)
        _setup_fut_validation(validate=False)
        return _setup_fut_validation

    # Set up inter-element communication based on the dropdown menu.
    # Items are: (target element ID, model name, whether to include PTS rasters
    static_map_generators = [
        ('sediment_static_maps', 'sediment', True),
        ('nutrient_static_maps', 'nutrient', True),
        ('carbon_static_maps', 'carbon', False),
        ('custom_static_maps', 'custom', False),
    ]
    for elem_id, model_name, include_pts in static_map_generators:
        target_element = ui_obj.find_element(elem_id)
        future_type_elem.value_changed.register(_setup_future_validation(
            model_name, target_element, include_pts))

def main(json_config=None):
    # add logging handler so this stuff is written to disk
    if json_config is None:
        logfile_filename = 'debug_unknown'
    else:
        logfile_filename = 'debug_%s' % json_config.replace('.json', '')
    logfile_filename = os.path.basename(logfile_filename)
    logfile_path = os.path.join(os.getcwd(), '..', logfile_filename +
        '.txt')
    debug_handler = logging.FileHandler(logfile_path, 'w', encoding='utf-8')
    LOGGER.addHandler(debug_handler)
    PALISADES_LOGGER.addHandler(debug_handler)
    LOGGER.debug('Writing logfile to %s', logfile_path)

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
        dist_data = json.load(open(os.path.join(exe_dir, 'dist_version.json')))
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
        dist_data = versioning.build_data()
        dist_data['dist_name'] = 'OPAL'  # we are for sure for OPAL only
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
    form_window.app_info_dialog.setWindowTitle('About OPAL')
    opal_info_text = "OPAL %s<br/><br/>" % dist_data['version_str']
    opal_info_text += '<a href="naturalcapitalproject.org">naturalcapitalproject.org</a>'
    form_window.app_info_dialog.set_body_text(opal_info_text)
    form_window.app_info_dialog.set_icon(opal_logo, scale=True)

    #form_window.menu_bar.addMenu(help_menu)
    form_window.layout().setMenuBar(form_window.menu_bar)

    # start the interactive application
    gui_app.execute()

if __name__ == '__main__':
    main()

