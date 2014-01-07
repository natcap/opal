
import os

from invest_natcap.wind_energy import wind_energy

source_dir = 'data/colombia_tool_data'
out_dir = 'data/colombia_clipped'

aoi = os.path.join(source_dir, 'sample_aoi.shp')
servicesheds = 'Servicesheds_Col.shp'
reservoirs = 'Reservoirs.shp'
ecosystems = 'Ecosystems_Colombia.shp'

for vector in [servicesheds, reservoirs, ecosystems]:
    print 'starting %s' % vector
    in_vector = os.path.join(source_dir, vector)
    out_vector = os.path.join(out_dir, vector.lower())
    wind_energy.clip_datasource(aoi, in_vector, out_vector)
