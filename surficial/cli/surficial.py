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
from surficial.cli import defaults

# default palette
BLUE = '#6699cc'
BLACK = '#000000'
GREEN = '#18b04c'
RED = '#ff3caa'
ORANGE = '#f8af1e'
BROWN = '#ab7305'

def load_style(style_f):
    import json

    with open(style_f, 'r') as style_src:
        styles = json.load(style_src)
        #for section, data in styles.items():
        #    print(section)
    return styles

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
            if feature_src.schema['geometry'] in ['LineString', 'Point']:
                logging.warn('File: {} is 2D. Please provide an elevation source'.format(feature_f))
            geometries = [shape(feature['geometry']) for feature in feature_src]
        feature_crs = feature_src.crs_wkt

    return feature_crs, geometries

def remove_spikes(vertices):
    """
    Expanding minimum from upstream to downstream
    """
    zmin = vertices.groupby(pnd.Grouper(key='edge')).expanding().min()['z'].reset_index(drop=True)
    zmin.name = 'zmin'
    result = pnd.concat([vertices, zmin], axis=1)

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
@click.option('--despike/--no-despike', is_flag=True, default=True,
              help="Eliminate elevation up-spikes from the stream profile")
@click.option('--invert/--no-invert', is_flag=True, default=True,
              help="Invert the x-axis")
@click.option('--station', nargs=1, type=click.FLOAT, metavar='<float>',
              help="Densify lines with regularly spaced stations")
@click.option('--style', 'style_f', nargs=1, type=click.Path(exists=True), metavar='<style_file>',
              help="YAML file containing plot styles")
@click.option('-e', '--exaggeration', nargs=1, type=click.INT, default=100, metavar='<int>',
              help="Vertical exaggeration of the profile")
@click.option('-v', '--verbose', is_flag=True,
              help='Enables verbose mode')
def profile(stream_f, elevation_f, terrace_f, feature_f, label, despike, invert, station, style_f, exaggeration, verbose):
    """
    Plots a long profile

    \b
    Example:
    surficial profile stream_ln.shp elevation_utm.tif --terrace terrace_pt_utm.shp --features feature_pt_utm.shp

    """    
    from matplotlib.collections import LineCollection

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
    if despike:
        vertices = remove_spikes(vertices)

    styles = defaults.styles.copy()
    if style_f:
        user_styles = load_style(style_f)
        styles.update(user_styles)

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

    profile_verts = [list(zip(edge_verts['s'], edge_verts['z'])) for _, edge_verts in vertices.groupby(pnd.Grouper(key='edge'))]
    profile_lines = LineCollection(profile_verts, **styles.get('stream'))
    ax.add_collection(profile_lines)

    if despike:
        despiked_verts = [list(zip(edge_verts['s'], edge_verts['zmin'])) for _, edge_verts in vertices.groupby(pnd.Grouper(key='edge'))]
        despiked_lines = LineCollection(despiked_verts, **styles.get('despiked'))
        ax.add_collection(despiked_lines)
    if feature_f:
        _, feature_pt = read_geometries(feature_f, elevation_f=elevation_f)
        feature_hits = surficial.project_buffer_contents(graph, feature_pt, 100, reverse=True)
        feature_addresses = surficial.address_point_df(feature_hits, edge_addresses)
        features, = ax.plot(feature_addresses['ds'], feature_addresses['z'], **styles.get('features'))
    if terrace_f:
        _, terrace_pt = read_geometries(terrace_f, elevation_f=elevation_f)
        hits = surficial.project_buffer_contents(graph, terrace_pt, 50, reverse=True)
        point_addresses_right = surficial.address_point_df(hits[(hits.d < 0)], edge_addresses)
        point_addresses_left = surficial.address_point_df(hits[(hits.d >= 0)], edge_addresses)
        terrace_left, = ax.plot(point_addresses_left['ds'], point_addresses_left['z'], **styles.get('terrace').get('left'))
        terrace_right, = ax.plot(point_addresses_right['ds'], point_addresses_right['z'], **styles.get('terrace').get('right'))
    if invert:
        ax.invert_xaxis()
    ax.set(aspect=exaggeration,
           xlabel='Distance ({})'.format(unit.lower()),
           ylabel='Elevation ({0}), {1}x v.e.'.format(unit.lower(), exaggeration))
    plt.legend(handles=[features, terrace_left, terrace_right, profile_lines, despiked_lines])
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
    from matplotlib.collections import LineCollection

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

    edge_lines = [list(zip(edge_data['x'], edge_data['y'])) for _, edge_data in vertices.groupby(pnd.Grouper(key='edge'))]
    edge_collection = LineCollection(edge_lines, color=BLUE, linestyle='-', linewidth=1.4, alpha=1.0, label='stream')
    ax.add_collection(edge_collection)

    if terrace_f:
        _, terrace_pt = read_geometries(terrace_f)
        ax.plot([p.coords.xy[0] for p in terrace_pt], [p.coords.xy[1] for p in terrace_pt],
            color=ORANGE, marker='o', markersize=4, linestyle='None', alpha=0.5, label='terrace')
    if feature_f:
        _, feature_pt = read_geometries(feature_f)
        ax.plot([p.coords.xy[0] for p in feature_pt], [p.coords.xy[1] for p in feature_pt],
            color=RED, marker='o', linestyle='None', label='features')
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
