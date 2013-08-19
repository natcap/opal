import versioning
import sys

import adept_core

# The __version__ attribute MUST be set to 'dev'.  It is changed automatically
# when the package is built.  The build_attrs attribute is set at the same time,
# but it instead contains a list of attributes of __init__.py that are related
# to the build.
__version__ = 'dev'
build_data = None

if __version__ == 'dev' and build_data == None:
    __version__ = versioning.version()
    build_data = versioning.build_data()
    for key, value in sorted(build_data.iteritems()):
        setattr(sys.modules[__name__], key, value)

    del sys.modules[__name__].key
    del sys.modules[__name__].value

execute = adept_core.execute
