import palisades

print "Build data"
for attr in palisades.build_data:
    print "%s: %s" % (attr, getattr(palisades, attr, False))

palisades.launch('adept.json')
