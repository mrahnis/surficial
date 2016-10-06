import sys
import logging

import networkx as nx
from gdal import osr
import fiona
import rasterio
from shapely.geometry import shape
#from descartes import PolygonPatch
import matplotlib.pyplot as plt
import pandas as pnd
import click

import drapery
import surficial

# default palette
BLUE = '#6699cc'
BLACK = '#000000'
GREEN = '#18b04c'
RED = '#ff3caa'
ORANGE = '#f8af1e'
BROWN = '#ab7305'

def read_geometries(feature_f, elevation_f=None):
    """
    Read and drape line geometries
    """
    with fiona.open(feature_f) as feature_src:
        supported = ['Point', 'LineString', '3D Point', '3D LineString']
        if feature_src.schema['geometry'] not in supported:
            logging.error('Geometry must be one of: {}'.format(supported))
        if elevation_f:
            with rasterio.open(elevation_f) as raster:
                if feature_src.crs != raster.crs:
                    logging.error('CRS for {} and {} are different'.format(feature_f, elevation_f))
                geometries = [drapery.drape(raster, feature) for feature in feature_src]
        else:
            geometries = [shape(feature['geometry']) for feature in feature_src]
            if feature_src.schema['geometry'] in ['LineString', 'Point']:
                logging.warn('File: {} is 2D. Please provide an elevation source'.format(feature_f))
        feature_crs = feature_src.crs_wkt

    return feature_crs, geometries

def flatten_spikes(vertices):
    """
    Expanding minimum from upstream to downstream
    """
    vertices_zmin = vertices.groupby(pnd.Grouper(key='edge')).expanding().min()['z'].reset_index(drop=True)
    vertices_zmin.name = 'zmin'
    result = pnd.concat([vertices, vertices_zmin], axis=1)

    return result

"""
def annotate_features(ax, features):
    for measure, feature in features.iterrows():
        offset = 10
        ha = 'left'
        va = 'bottom'
        color = 'black'

        verts = [(measure, feature['ELEVATION']), (measure, feature['ELEVATION'] + offset)]
        codes = [Path.MOVETO, Path.LINETO]
        path = Path(verts, codes)
        patch = patches.PathPatch(path, color=color)
        ax.add_patch(patch)
        ax.text(measure, feature['ELEVATION']+offset, feature['LABEL'], color=color, rotation=30, rotation_mode='anchor', ha=ha, va=va)
    return ax
"""

@click.group()
def cli():
    pass

@click.command(options_metavar='<options>')
@click.argument('stream_f', nargs=1, type=click.Path(exists=True), metavar='<stream_file>')
@click.argument('elevation_f', nargs=1, type=click.Path(exists=True), metavar='<dem_file>')
@click.option('--terrace', 'terrace_f', nargs=1, type=click.Path(exists=True), metavar='<terrace_file>',
              help="Points to project onto the profile")
@click.option('--features', 'feature_f', nargs=1, type=click.Path(exists=True), metavar='<features_file>',
              help="Features of interest")
@click.option('--label/--no-label', is_flag=True, default=False,
              help="Label features from a given field in the features dataset")
@click.option('--flatten/--no-flatten', is_flag=True, default=True,
              help="Eliminate elevation spikes from the stream profile")
@click.option('--invert/--no-invert', is_flag=True, default=True,
              help="Invert the x-axis")
@click.option('--station', nargs=1, type=click.FLOAT, metavar='<float>',
              help="Densify lines with regularly spaced stations")
@click.option('-e', '--exaggeration', nargs=1, type=click.INT, default=100, metavar='<int>',
              help="Vertical exaggeration of the profile")
@click.option('-v', '--verbose', is_flag=True,
              help='Enables verbose mode')
def profile(stream_f, elevation_f, terrace_f, feature_f, label, flatten, invert, station, exaggeration, verbose):
    """
    Plots a long profile

    \b
    Example:
    surficial profile stream_ln.shp elevation_utm.tif --terrace terrace_pt_utm.shp --features feature_pt_utm.shp

    """

    if verbose is True:
        loglevel = 2
    else:
        loglevel = 0

    logging.basicConfig(stream=sys.stderr, level=loglevel or logging.INFO)
    logger = logging.getLogger('surficial')

    stream_crs, lines = read_geometries(stream_f, elevation_f=elevation_f)
    crs=osr.SpatialReference(wkt=stream_crs)
    if crs.IsProjected:
        unit = crs.GetAttrValue('unit')
    else:
        logger.error("Data are not projected")

    graph = surficial.construct(lines)
    edge_addresses = surficial.address_edges(graph, surficial.get_outlet(graph))
    vertices = surficial.station(graph, 10, keep_vertices=True)
    if flatten:
        vertices = flatten_spikes(vertices)

    """
    # make it a list instead of generator so i can reuse
    path1= list(surficial.get_path_edges(g, 1, outlet))
    # buffer the edges and make a patch
    buf = PolygonPatch(surficial.get_edge_buffer(g, 100.0, edges=path1), fc=BLUE, ec=BLUE, alpha=0.5, zorder=2)
    # project points within 50 ft onto the path
    hits = surficial.project_buffer_contents(g, path1, terrace_pt, 50, reverse=True)
    # address the points
    point_addresses = surficial.address_point_df(hits, edge_addresses)
    """

    fig = plt.figure()

    ax = fig.add_subplot(111)
    for _, edge_data in vertices.groupby(pnd.Grouper(key='edge')):
        ax.plot(edge_data['s'], edge_data['z'],
            color=BLACK, marker='None', linestyle='-', linewidth=1.2, alpha=0.3, label='profile')
        if flatten:
            ax.plot(edge_data['s'], edge_data['zmin'],
                color=BLUE, marker='None', linestyle='-', linewidth=1.4, alpha=1.0, label='profile')
    if feature_f:
        _, feature_pt = read_geometries(feature_f, elevation_f=elevation_f)
        feature_hits = surficial.project_buffer_contents(graph, feature_pt, 100, reverse=True)
        feature_addresses = surficial.address_point_df(feature_hits, edge_addresses)
        ax.plot(feature_addresses['ds'], feature_addresses['z'],
            color=RED, marker='o', linestyle='None', label='profile')
    if terrace_f:
        _, terrace_pt = read_geometries(terrace_f, elevation_f=elevation_f)
        hits = surficial.project_buffer_contents(graph, terrace_pt, 50, reverse=True)
        point_addresses_right = surficial.address_point_df(hits[(hits.d < 0)], edge_addresses)
        point_addresses_left = surficial.address_point_df(hits[(hits.d >= 0)], edge_addresses)
        ax.plot(point_addresses_left['ds'], point_addresses_left['z'],
            color=ORANGE, marker='o', markersize=4, markeredgecolor='None', linestyle='None', alpha=0.5, label='profile')
        ax.plot(point_addresses_right['ds'], point_addresses_right['z'],
            color=BROWN, marker='o', markersize=4, fillstyle='none', linestyle='None', label='profile')
    if invert:
        ax.invert_xaxis()
    ax.set(aspect=exaggeration,
           xlabel='Distance ({})'.format(unit.lower()),
           ylabel='Elevation ({0}), {1}x v.e.'.format(unit.lower(), exaggeration))
    plt.show()

@click.command(options_metavar='<options>')
@click.argument('stream_f', nargs=1, type=click.Path(exists=True), metavar='<stream_file>')
@click.option('--terrace', 'terrace_f', nargs=1, type=click.Path(exists=True), metavar='<terrace_file>',
              help="Points to project onto the profile")
@click.option('--features', 'feature_f', nargs=1, type=click.Path(exists=True), metavar='<features_file>',
              help="Features of interest")
@click.option('-v', '--verbose', is_flag=True,
              help='Enables verbose mode')
def plan(stream_f, terrace_f, feature_f, verbose):
    """
    Plots a planview map

    \b
    Example:
    surficial plan stream_ln.shp --terrace terrace_pt_utm.shp --features feature_pt_utm.shp

    """

    if verbose is True:
        loglevel = 2
    else:
        loglevel = 0

    logging.basicConfig(stream=sys.stderr, level=loglevel or logging.INFO)
    logger = logging.getLogger('surficial')

    stream_crs, lines = read_geometries(stream_f)
    crs=osr.SpatialReference(wkt=stream_crs)
    if crs.IsProjected:
        unit = crs.GetAttrValue('unit')
    else:
        logger.error("Data are not projected")

    graph = surficial.construct(lines)
    edge_addresses = surficial.address_edges(graph, surficial.get_outlet(graph))
    vertices = surficial.station(graph, 10, keep_vertices=True)

    fig = plt.figure()

    ax = fig.add_subplot(111)
    for _, edge_data in vertices.groupby(pnd.Grouper(key='edge')):
        ax.plot(edge_data['x'], edge_data['y'],
            color=BLUE, marker='None', linestyle='-', linewidth=1.4, alpha=1.0, label='map')
    if terrace_f:
        _, terrace_pt = read_geometries(terrace_f)
        ax.plot([p.coords.xy[0] for p in terrace_pt], [p.coords.xy[1] for p in terrace_pt],
            color=ORANGE, marker='o', markersize=4, linestyle='None', alpha=0.5, label='map')
    if feature_f:
        _, feature_pt = read_geometries(feature_f)
        ax.plot([p.coords.xy[0] for p in feature_pt], [p.coords.xy[1] for p in feature_pt],
            color=RED, marker='o', linestyle='None', label='map')
    ax.set(aspect=1,
           xlabel='Easting ({})'.format(unit.lower()),
           ylabel='Northing ({})'.format(unit.lower()))
    plt.show()

@click.command(options_metavar='<options>')
@click.argument('stream_f', nargs=1, type=click.Path(exists=True), metavar='<stream_file>')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode')
def network(stream_f, verbose):
    """
    Plots the network graph

    \b
    Example:
    surficial network stream_ln.shp

    """

    if verbose is True:
        loglevel = 2
    else:
        loglevel = 0

    logging.basicConfig(stream=sys.stderr, level=loglevel or logging.INFO)
    logger = logging.getLogger('surficial')

    with fiona.open(stream_f) as stream_src:
        lines = [shape(line['geometry']) for line in stream_src]

    graph = surficial.construct(lines)

    # plot
    fig = plt.figure()
    ax = fig.add_subplot(111)
    nx.draw(graph, ax=ax, with_labels=True, node_color='w')

    plt.show()

cli.add_command(profile)
cli.add_command(plan)
cli.add_command(network)
