# -*- coding: utf-8 -*-

import os
import codecs

DATA = os.path.join(os.path.dirname(__file__), '..', 'data',
    'colombia_tool_data')
LULC_NATURAL = {
    'Aguas cont. artificiales': False,  # artificial bodies of water
    'Afloramientos rocosos': False, # rocky outcrops
    'Aguas cont. naturales': False, # Natural bodies of water
    'Arbustales': True, # shrubs
    'Áreas agrícolas heterogéneas': True, # Heterogeneous ag. areas
    'Áreas mayormente alteradas': True, # Mostly disturbed areas
    'Áreas urbanas': False, # Urban areas
    'Bosques naturales': True, # Natural forest
    'Bosques plantados': True, # Planted forest
    'Cultivos anuales o transitorios': True, # annual or seasonal crops
    'Cultivos semipermanentes y permanentes': True, # Perm. or semiperm. crops
    'Glaciares y nieves': False, # Glaciers and snows
    'Herbáceas y arbustivas': True, # Herbaceous and shrub
    'Herbazales': True, # Grassland
    'Hidrofitia': True, # Herbaceous vegetation of inland wet areas.  Wetlands.
    'Isla de Malpelo': False, # Very rocky island off the coast of Colombia
    'Lagunas': False, # lakes
    'Manglar': True, # Mangrove swamp
    'Pastos': True, # Pastures
    'Vegetación secundaria': True, # secondary vegetation
    'Zonas desnudas': False, # bare areas.
}

def add_lulc_veg(in_uri, out_uri):
    input_file = open(in_uri, 'rU')
    # read the headers
    headers = input_file.next()

    # open up the output file for writing.
    out_file = codecs.open(out_uri, 'wU', 'iso-8859-1')
    new_headers = headers.rstrip() + ',%s\n' % 'LULC_veg'
    out_file.write(new_headers)

    for line in input_file:
        # The Biophysical_Colombia is Latin-1 (iso-8859-1), so we need to
        # convert to UTF-8 to match the encoding of this file.
        line = line.decode('iso-8859-1').encode('utf-8')
        found = False
        is_natural = False
        for key in LULC_NATURAL.keys():
            if line.startswith(key):
                found = True
                is_natural = LULC_NATURAL[key]
                break

        if not found:
            raise Exception('Line did not match any known habitats: %s' % line)
        line = line.decode('utf-8').encode('iso-8859-1').replace('\n', '')
        print line

        comma = unicode(',', 'iso-8859-1')
        is_natural = unicode(str(int(is_natural)), 'iso-8859-1')
        newline = unicode('\n', 'iso-8859-1')

        out_file.write(line + comma + is_natural + newline)



if __name__ == '__main__':
    add_lulc_veg(os.path.join(DATA, 'Biophysical_Colombia.csv'), 'new.csv')

