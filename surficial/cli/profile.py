import sys
import logging

import networkx as nx
import fiona
from shapely.geometry import shape, mapping, Point, LineString
from descartes import PolygonPatch
import matplotlib.pyplot as plt
import pandas as pnd
import click

import drapery
import surficial

@click.group()
def cli():
    pass

@click.command(options_metavar='<options>')
@click.argument('stream_f', nargs=1, type=click.Path(exists=True), metavar='<stream_file>')
@click.argument('elevation_f', nargs=1, type=click.Path(exists=True), metavar='<dem_file>')
@click.option('--terrace', 'terrace_f', nargs=1, type=click.Path(exists=True), metavar='<terrace_file>', help="Points to project onto the profile")
@click.option('--features', 'feature_f', nargs=1, type=click.Path(exists=True), metavar='<features_file>', help="Features of interest")
@click.option('--smooth/--no-smooth', is_flag=True, default=True, help="Eliminate elevation spikes from the stream profile")
@click.option('--station', nargs=1, type=click.FLOAT, metavar='<float>', help="Densify line vertices with regularly spaced stations")
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode')
def plot(stream_f, terrace_f, elevation_f, feature_f, smooth, station, verbose):
	"""
	Plots a long profile
	
	\b
	Example:
	profile plot .\examples\piney-run\stream_ln_z.shp .\examples\piney-run\elevation_utm.tif --terrace .\examples\piney-run\terrace_pt_utm.shp --features .\examples\piney-run\feature_pt_utm.shp
	
	"""

	if verbose is True:
		loglevel = 2
	else:
		loglevel = 0

	logging.basicConfig(stream=sys.stderr, level=loglevel or logging.INFO)
	logger = logging.getLogger('surficial')

	BLUE = '#6699cc'

	# stream
	with fiona.open(stream_f) as stream_src:
		stream_crs = stream_src.crs
		if stream_src.schema['geometry'] == '3D LineString':
			lines = [shape(line['geometry']) for line in stream_src]
		elif stream_src.schema['geometry'] == 'LineString':
			#lines = drapery.add_height_line(elevation_f, [shape(line['geometry']) for line in stream_src])
			lines = drapery.add_height_line(elevation_f, stream_src)
		else:
			logger.error('Stream geometry must be a LineString or 3D LineString')
	# make the graph
	g = surficial.construct(lines)
	outlet = surficial.get_outlet(g)
	edge_addresses = surficial.address_edges(g, outlet)
	vertices = surficial.station(g, 10, keep_vertices=True)

	# do expanding min and concat
	if smooth:
		vertices_zmin = vertices.groupby(pnd.Grouper(key='edge')).expanding().min()['z'].reset_index(drop=True)
		vertices_zmin.name = 'zmin'
		vertices = pnd.concat([vertices, vertices_zmin], axis=1)

	# terrace points
	if terrace_f:
		with fiona.open(terrace_f) as terrace_src:
			#terrace_pt = drapery.add_height_points(elevation_f, [shape(point['geometry']) for point in terrace_src])
			terrace_pt = drapery.add_height_points(elevation_f, terrace_src)
			terrace_crs = terrace_src.crs
			if stream_crs != terrace_crs:
				logger.error('CRS for stream lines and terrace points are not the same.')
		# make it a list instead of generator so i can reuse
		path1= list(surficial.get_path_edges(g, 1, outlet))
		# buffer the edges and make a patch
		buf = PolygonPatch(surficial.get_edge_buffer(g, 100.0, edges=path1), fc=BLUE, ec=BLUE, alpha=0.5, zorder=2)
		# project points within 50 ft onto the path
		hits = surficial.project_buffer_contents(g, path1, terrace_pt, 50, reverse=True)
		# address the points
		point_addresses = surficial.address_point_df(hits, edge_addresses)

	if feature_f:
		with fiona.open(feature_f) as feature_src:
			if feature_src.crs != stream_crs:
				logger.error('CRS for stream lines and feature points are not the same.')
			#feature_pt = drapery.add_height_points(elevation_f, [shape(point['geometry']) for point in feature_src])
			feature_pt = drapery.add_height_points(elevation_f, feature_src)
			features_labels = [point['properties']['LABEL'] for point in feature_src]
		features_x = [p.coords.xy[0] for p in feature_pt]
		features_y = [p.coords.xy[1] for p in feature_pt]
		feature_hits = surficial.project_buffer_contents(g, g.edges(), feature_pt, 100, reverse=True)
		feature_addresses = surficial.address_point_df(feature_hits, edge_addresses)

	# plot
	fig = plt.figure()

	ax1 = fig.add_subplot(121)
	for group, df in vertices.groupby(pnd.Grouper(key='edge')):
		ax1.plot(df['x'], df['y'], color=BLUE, marker='None', linestyle='-', alpha=0.5, label='map')
	terrace_x = [p.coords.xy[0] for p in terrace_pt]
	terrace_y = [p.coords.xy[1] for p in terrace_pt]
	ax1.plot(terrace_x, terrace_y, color='green', marker='.', linestyle='None', alpha=0.5, label='map')
	ax1.add_patch(buf)
	if feature_f:
		ax1.plot(features_x, features_y, color='orange', marker='o', linestyle='None', label='map')
	ax1.set_aspect(1)

	ax2 = fig.add_subplot(122)
	for group, df in vertices.groupby(pnd.Grouper(key='edge')):
		ax2.plot(df['s'], df['z'], color='black', marker='None', linestyle='-', alpha=0.3, label='profile')
		if smooth:
			ax2.plot(df['s'], df['zmin'], color=BLUE, marker='None', linestyle='-', alpha=0.5, label='profile')
		if feature_f:
			ax2.plot(feature_addresses['ds'], feature_addresses['z'], color='orange', marker='o', linestyle='None', label='profile')
	ax2.plot(point_addresses['ds'], point_addresses['z'], color='green', marker='.', linestyle='None', alpha=0.5, label='profile')
	ax2.invert_xaxis()
	ax2.set_aspect(100)

	plt.show()


@click.command(options_metavar='<options>')
@click.argument('stream_f', nargs=1, type=click.Path(exists=True), metavar='<stream_file>')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode')
def graph(stream_f, verbose):
	"""
	Plots the network graph
	
	\b
	Example:
	profile graph .\examples\piney-run\stream_ln_z.shp
	
	"""

	if verbose is True:
		loglevel = 2
	else:
		loglevel = 0

	logging.basicConfig(stream=sys.stderr, level=loglevel or logging.INFO)
	logger = logging.getLogger('surficial')

	# stream
	with fiona.open(stream_f) as stream_src:
		lines = [shape(line['geometry']) for line in stream_src]
		stream_crs = stream_src.crs

	# make the graph
	g = surficial.construct(lines)
	outlet = surficial.get_outlet(g)

	# plot
	fig = plt.figure()
	ax = fig.add_subplot(111)
	nx.draw(g, ax=ax, with_labels=True, node_color='w')

	plt.show()

cli.add_command(plot)
cli.add_command(graph)