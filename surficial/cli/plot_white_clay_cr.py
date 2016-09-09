import networkx as nx
import fiona
from shapely.geometry import shape, mapping, Point, LineString
import matplotlib.pyplot as plt
import pandas as pnd
from descartes import PolygonPatch

import profile
#from ops.graph import *
#from ops.raster import *

stream_ln_fn = "../examples/white-clay-cr/stream_ln_nhd_sp.shp"
elevation_tif = "../examples/white-clay-cr/bare_earth"

# stream
# stream_ln = fiona.open(stream_ln_fn)
# stream_ln_z = [profile.add_height_line(elevation_tif, shape(line['geometry'])) for line in stream_ln]

with fiona.open(stream_ln_fn, 'r') as stream_ln:
	stream_ln_z = [profile.add_height_line(elevation_tif, shape(line['geometry'])) for line in stream_ln]

g = profile.construct(stream_ln_z)

stream_ln.close()

outlet = profile.get_outlet(g)

# get a dataframe of regularly spaced stations
# def stations_to_df(g, step):
# return a dataframe
stations_arr = []
for u, v, data in g.edges(data=True):
	# get the distance from the upstream node to the outlet
	path = profile.get_path_edges(g, u, outlet)
	path_len = profile.get_path_weight(g, path, 'len')

	# def station_interpolate(geom, step):
	# return a 2d array
	line = data['geom']
	d = 0
	while d < line.length:
		s = path_len - d
		p = line.interpolate(d)
		stations_arr.append([s, p.x, p.y, p.z, (u,v)])
		d += 10.0
stations = pnd.DataFrame(stations_arr, columns=['s','x','y','z','edge'])

# get a dataframe of the vertices
# def vertices_to_df(g):
verts = pnd.DataFrame()
for u, v, data in g.edges(data=True):
	verts_arr = []
	# get the distance from the upstream node to the outlet
	path = profile.get_path_edges(g, u, outlet)
	path_len = profile.get_path_weight(g, path, 'len')

	line = data['geom']
	for p in list(line.coords):
		s = path_len - line.project(Point(p))
		verts_arr.append([s, p[0], p[1], p[2], (u, v)])
	edge_verts = pnd.DataFrame(verts_arr, columns=['s','x','y','z','edge'])
	edge_verts['zmin'] = pnd.expanding_min(edge_verts['z'])
	verts = pnd.concat([verts, edge_verts])

BLUE = '#6699cc'

# plot
fig = plt.figure()

ax1 = fig.add_subplot(221)
nx.draw(g, ax=ax1, with_labels=True, node_color='w')

ax2 = fig.add_subplot(222)
ax2.plot(verts['x'], verts['y'], color='black', marker='.', linestyle='None', alpha=0.5, label='map')
ax2.set_aspect(1)

ax3 = fig.add_subplot(212)
ax3.plot(verts['s'], verts['z'], color='black', marker='.', linestyle='None', alpha=0.5, label='profile')

ax3.plot(verts['s'], verts['zmin'], color=BLUE, marker='.', linestyle='None', alpha=0.5, label='profile')
ax3.invert_xaxis()
ax3.set_aspect(1000)

plt.show()
