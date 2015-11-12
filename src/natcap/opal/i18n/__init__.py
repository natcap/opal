# -*- coding: utf-8 -*-

import os, sys
import locale
import gettext
import logging

LOGGER = logging.getLogger('natcap.opal.i18n')

# Change this variable to your app name!
#  The translation files will be under
#  @LOCALE_DIR@/@LANGUAGE@/LC_MESSAGES/@APP_NAME@.mo
APP_NAME = "adept"

# This is ok for maemo. Not sure in a regular desktop:
# assume we're executing from the adept source root.
LOCALE_DIR = os.path.join(os.path.dirname(__file__), 'locale') # .mo files will then be located
                                           #in APP_Dir/i18n/LANGUAGECODE/LC_MESSAGES/

# Now we need to choose the language. We will provide a list, and gettext
# will use the first translation available in the list
#
#  In maemo it is in the LANG environment variable
#  (on desktop is usually LANGUAGES)
DEFAULT_LANGUAGES = os.environ.get('LANG', '').split(':')
DEFAULT_LANGUAGES += ['en_US']

lc, encoding = locale.getdefaultlocale()
if lc:
    languages = [lc]

# Concat all languages (env + default locale),
#  and here we have the languages and location of the translations
languages += DEFAULT_LANGUAGES
mo_location = LOCALE_DIR

# Lets tell those details to gettext
#  (nothing to change here for you)
gettext.install(APP_NAME, localedir=None, unicode=1)

gettext.find(APP_NAME, mo_location)

gettext.textdomain(APP_NAME)

gettext.bind_textdomain_codeset(APP_NAME, "UTF-8")

LOGGER.debug('Available languages: %s', languages)
#language = gettext.translation(APP_NAME, mo_location,
#    languages=languages, fallback=True)

# KEEP FALLBACK=TRUE!
# This module is imported when running setup.py, but the language translation
# files have not been loaded to the correct place.  If Fallback=False, an
# exception will be raised at that time.
get_trans = lambda code: gettext.translation(APP_NAME, mo_location,
        languages=[code], fallback=True)

class Language(object):
    def __init__(self):
        self.current_lang = 'en'

        self.available_langs = {
            'en': get_trans('en'),
            'es': get_trans('es'),
        }

    def __call__(self):
        print 'current language is %s' % self.current_lang
        current_language = self.available_langs[self.current_lang]
        current_language.install()
        return current_language

    def _lang(self):
        return self.available_langs[self.current_lang]

    def set(self, lang_code):
        self.current_lang = lang_code
        print 'setting current lang to %s' % lang_code
        self.__call__()  # install the new language.

    def ugettext(self, message):
        self._lang().install()
        return self._lang().ugettext(message)

    def info(self):
        return self._lang().info()

language = Language()

def current_lang():
    """Return the string language code of the currently-active language."""
    return language.info()['language']

def os_default_lang():
    """Return the OS default language."""
    return locale.getdefaultlocale()[0].split('_')[0].lower()
