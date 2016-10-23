import sys

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

def load_style(styles_f):
    """
    Load a json file containing the keyword arguments to use for plot styling
    """
    import json

    with open(styles_f, 'r') as styles_src:
        styles = json.load(styles_src)
    return styles

def read_geometries(feature_f, elevation_f=None, keep_z=False):
    """
    Read and drape line geometries
    """
    with fiona.open(feature_f) as feature_src:
        supported = ['Point', 'LineString', '3D Point', '3D LineString']
        if feature_src.schema['geometry'] not in supported:
            raise click.BadParameter('Geometry must be one of: {}'.format(supported))
        if elevation_f and not keep_z:
            with rasterio.open(elevation_f) as raster:
                if feature_src.crs != raster.crs:
                    raise click.BadParameter('{} and {} use different CRS'.format(feature_f, elevation_f))
                geometries = [drapery.drape(raster, feature) for feature in feature_src]
        else:
            if feature_src.schema['geometry'] in ['LineString', 'Point'] and not keep_z:
                raise click.BadParameter('{} is 2D. Provide an elevation source, or convert to 3D geometry'.format(feature_f))
            geometries = [shape(feature['geometry']) for feature in feature_src]

        feature_crs = feature_src.crs_wkt

    return feature_crs, geometries

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
@click.pass_context
@click.version_option(version=surficial.__version__, message='%(version)s')
def cli(ctx):
    pass

@click.command(options_metavar='<options>')
@click.argument('stream_f', nargs=1, type=click.Path(exists=True), metavar='<stream_file>')
@click.argument('elevation_f', nargs=1, type=click.Path(exists=True), metavar='<dem_file>')
@click.option('--points', 'point_multi_f', type=(click.Path(exists=True), click.STRING), multiple=True, metavar='<point_file> <style>',
              help='Points to project onto profile using a given style')
@click.option('--styles', 'styles_f', nargs=1, type=click.Path(exists=True), metavar='<styles_file>',
              help="JSON file containing plot styles")
@click.option('--label/--no-label', is_flag=True, default=False,
              help="Label features from a given field in the features dataset")
@click.option('--despike/--no-despike', is_flag=True, default=True,
              help="Eliminate elevation up-spikes from the stream profile")
@click.option('--station', nargs=1, type=click.FLOAT, metavar='<float>',
              help="Densify lines with regularly spaced stations")
@click.option('--invert/--no-invert', is_flag=True, default=True,
              help="Invert the x-axis")
@click.option('-e', '--exaggeration', nargs=1, type=click.INT, default=100, metavar='<int>',
              help="Vertical exaggeration of the profile")
def profile(stream_f, elevation_f, point_multi_f, styles_f, label, despike, station, invert, exaggeration):
    """
    Plots a long profile

    \b
    Example:
    surficial profile stream_ln.shp elevation.tif --points feature_pt.shp features --points terrace_pt.shp terrace --styles styles.json

    """    
    from matplotlib.collections import LineCollection

    stream_crs, lines = read_geometries(stream_f, elevation_f=elevation_f)
    crs=osr.SpatialReference(wkt=stream_crs)
    if crs.IsProjected:
        unit = crs.GetAttrValue('unit')
    else:
        raise click.BadParameter('Data are not projected')

    alignment = surficial.Alignment(lines)

    edge_addresses = alignment.edge_addresses(alignment.outlet())

    vertices = alignment.station(10, keep_vertices=True)
    if despike:
        vertices = surficial.remove_spikes(vertices)

    styles = defaults.styles.copy()
    if styles_f:
        user_styles = load_style(styles_f)
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

    handles = []
    fig = plt.figure()
    ax = fig.add_subplot(111)

    profile_verts = [list(zip(edge_verts['s'], edge_verts['z'])) for _, edge_verts in vertices.groupby(pnd.Grouper(key='edge'))]
    profile_lines = LineCollection(profile_verts, **styles.get('stream'))
    ax.add_collection(profile_lines)

    if despike:
        despiked_verts = [list(zip(edge_verts['s'], edge_verts['zmin'])) for _, edge_verts in vertices.groupby(pnd.Grouper(key='edge'))]
        despiked_lines = LineCollection(despiked_verts, **styles.get('despiked'))
        ax.add_collection(despiked_lines)
    for point_f, style_key in point_multi_f:
        _, point_geoms = read_geometries(point_f, elevation_f=elevation_f)
        hits = surficial.points_to_edge_addresses(alignment, point_geoms, 100, reverse=True)
        if 'left' and 'right' in styles.get(style_key):
            addresses_right = surficial.rebase_addresses(hits[(hits.d < 0)], edge_addresses)
            addresses_left = surficial.rebase_addresses(hits[(hits.d >= 0)], edge_addresses)
            points_left, = ax.plot(addresses_left['ds'], addresses_left['z'], **styles.get(style_key).get('left'))
            points_right, = ax.plot(addresses_right['ds'], addresses_right['z'], **styles.get(style_key).get('right'))
            handles.extend([points_left, points_right])
        else:
            addresses = surficial.rebase_addresses(hits, edge_addresses)
            points, = ax.plot(addresses['ds'], addresses['z'], **styles.get(style_key))
            handles.append(points)
    if invert:
        ax.invert_xaxis()
    ax.set(aspect=exaggeration,
           xlabel='Distance ({})'.format(unit.lower()),
           ylabel='Elevation ({0}), {1}x v.e.'.format(unit.lower(), exaggeration))
    handles.extend([profile_lines, despiked_lines])
    plt.legend(handles=handles)
    plt.show()

@click.command(options_metavar='<options>')
@click.argument('stream_f', nargs=1, type=click.Path(exists=True), metavar='<stream_file>')
@click.option('--points', 'point_multi_f', type=(click.Path(exists=True), click.STRING), multiple=True, metavar='<point_file> <style>',
              help='Points to project onto profile using a given style')
@click.option('--styles', 'styles_f', nargs=1, type=click.Path(exists=True), metavar='<styles_file>',
              help="JSON file containing plot styles")
def plan(stream_f, point_multi_f, styles_f):
    """
    Plots a planview map

    \b
    Example:
    surficial plan stream_ln.shp --points terrace_pt.shp terrace --points feature_pt.shp features

    """
    from matplotlib.collections import LineCollection

    stream_crs, lines = read_geometries(stream_f)
    crs=osr.SpatialReference(wkt=stream_crs)
    if crs.IsProjected:
        unit = crs.GetAttrValue('unit')
    else:
        raise click.BadParameter("Data are not projected")

    alignment = surficial.Alignment(lines)
    edge_addresses = alignment.edge_addresses(alignment.outlet())
    vertices = alignment.station(10, keep_vertices=True)

    styles = defaults.styles.copy()
    if styles_f:
        user_styles = load_style(styles_f)
        styles.update(user_styles)

    handles = []
    fig = plt.figure()
    ax = fig.add_subplot(111)

    edge_lines = [list(zip(edge_data['x'], edge_data['y'])) for _, edge_data in vertices.groupby(pnd.Grouper(key='edge'))]
    edge_collection = LineCollection(edge_lines, **styles.get('despiked'))
    ax.add_collection(edge_collection)

    for point_f, style_key in point_multi_f:
        _, point_geoms = read_geometries(point_f, keep_z=True)
        if 'left' and 'right' in styles.get(style_key):
            click.echo("Left and right styling not implemented in plan view; using left style only.")
            points, = ax.plot([p.coords.xy[0] for p in point_geoms], [p.coords.xy[1] for p in point_geoms], **styles.get(style_key).get('left'))
        else:
            points, = ax.plot([p.coords.xy[0] for p in point_geoms], [p.coords.xy[1] for p in point_geoms], **styles.get(style_key))
        handles.append(points)

    handles.append(edge_collection)
    ax.set(aspect=1,
           xlabel='Easting ({})'.format(unit.lower()),
           ylabel='Northing ({})'.format(unit.lower()))
    plt.legend(handles=handles)
    plt.show()

@click.command(options_metavar='<options>')
@click.argument('stream_f', nargs=1, type=click.Path(exists=True), metavar='<stream_file>')
def network(stream_f):
    """
    Plots the network graph

    \b
    Example:
    surficial network stream_ln.shp

    """

    with fiona.open(stream_f) as stream_src:
        lines = [shape(line['geometry']) for line in stream_src]

    graph = surficial.Alignment(lines)

    # plot
    fig = plt.figure()
    ax = fig.add_subplot(111)
    nx.draw(graph, ax=ax, with_labels=True, node_color='w')

    plt.show()

cli.add_command(profile)
cli.add_command(plan)
cli.add_command(network)
