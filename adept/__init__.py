import versioning

# The __version__ attribute MUST be set to 'dev'.  It is changed automatically
# when the package is built.  The build_data attribute is set at the same time.
__version__ = 'dev'
build_data = None

if __version__ == 'dev' and build_data == None:
    __version__ = versioning.version()
    build_data = versioning.build_data()
