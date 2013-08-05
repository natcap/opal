import versioning

# The __version__ attribute MUST be set to 'dev'.  It is changed automatically
# when the package is built.  The build_attrs attribute is set at the same time,
# but it instead contains a list of attributes of __init__.py that are related
# to the build.
__version__ = 'dev'
build_attrs= None

if __version__ == 'dev' and build_data == None:
    __version__ = versioning.version()
    build_data = versioning.build_data()
