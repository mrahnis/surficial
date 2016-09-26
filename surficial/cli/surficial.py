import sys
import logging

import networkx as nx
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
YELLOW = '#f8af1e'

"""
def _annotate_features(ax, features):
    # create some annotation for the features of interest
    # rather return patches
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
@click.option('--smooth/--no-smooth', is_flag=True, default=True,
              help="Eliminate elevation spikes from the stream profile")
@click.option('--station', nargs=1, type=click.FLOAT, metavar='<float>',
              help="Densify line vertices with regularly spaced stations")
@click.option('-v', '--verbose', is_flag=True,
              help='Enables verbose mode')
def profile(stream_f, elevation_f, terrace_f, feature_f, label, smooth, station, verbose):
    """
    Plots a long profile

    \b
    Example:
    surficial profile stream_ln.shp elevation_utm.tif --terrace terrace_pt_utm.shp --features feature_pt_utm.shp

    """

    def _read_lines(line_f, elevation_f):
        """
        Read and drape line geometries
        """
        with fiona.open(line_f) as line_src:
            if line_src.schema['geometry'] == '3D LineString':
                lines = [shape(line['geometry']) for line in line_src]
            elif line_src.schema['geometry'] == 'LineString':
                with rasterio.open(elevation_f) as raster:
                    lines = [drapery.drape(raster, line) for line in line_src]
            else:
                logger.error('Geometry must be a LineString or 3D LineString')

        return line_src.crs, lines

    def _read_points(point_f, elevation_f):
        """
        Read and drape point geometries
        """
        with fiona.open(point_f) as point_src:
            with rasterio.open(elevation_f) as raster:
                if point_src.crs != raster.crs:
                    logger.error('CRS for {} and {} are different'.format(point_src.crs, raster.crs))
                points = [drapery.drape(raster, point) for point in point_src]

        return point_src.crs, points

    def _smooth(vertices):
        """
        Expanding minimum from upstream to downstream
        """
        vertices_zmin = vertices.groupby(pnd.Grouper(key='edge')).expanding().min()['z'].reset_index(drop=True)
        vertices_zmin.name = 'zmin'
        result = pnd.concat([vertices, vertices_zmin], axis=1)

        return result

    if verbose is True:
        loglevel = 2
    else:
        loglevel = 0

    logging.basicConfig(stream=sys.stderr, level=loglevel or logging.INFO)
    logger = logging.getLogger('surficial')

    _, lines = _read_lines(stream_f, elevation_f)

    graph = surficial.construct(lines)
    edge_addresses = surficial.address_edges(graph, surficial.get_outlet(graph))
    vertices = surficial.station(graph, 10, keep_vertices=True)
    if smooth:
        vertices = _smooth(vertices)

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

    ax1 = fig.add_subplot(121)
    for _, edge_data in vertices.groupby(pnd.Grouper(key='edge')):
        ax1.plot(
            edge_data['x'], edge_data['y'],
            color=BLUE, marker='None', linestyle='-', alpha=0.5, label='map'
            )
    if terrace_f:
        _, terrace_pt = _read_points(terrace_f, elevation_f)
        ax1.plot(
            [p.coords.xy[0] for p in terrace_pt], [p.coords.xy[1] for p in terrace_pt],
            color=GREEN, marker='.', linestyle='None', alpha=0.5, label='map'
            )
    if feature_f:
        _, feature_pt = _read_points(feature_f, elevation_f)
        ax1.plot(
            [p.coords.xy[0] for p in feature_pt], [p.coords.xy[1] for p in feature_pt],
            color=YELLOW, marker='o', linestyle='None', label='map'
            )
    ax1.set_aspect(1)

    ax2 = fig.add_subplot(122)
    for _, edge_data in vertices.groupby(pnd.Grouper(key='edge')):
        ax2.plot(
            edge_data['s'], edge_data['z'],
            color=BLACK, marker='None', linestyle='-', alpha=0.3, label='profile'
            )
        if smooth:
            ax2.plot(
                edge_data['s'], edge_data['zmin'],
                color=BLUE, marker='None', linestyle='-', alpha=0.5, label='profile'
                )
    if feature_f:
        feature_hits = surficial.project_buffer_contents(
            graph, graph.edges(), feature_pt, 100, reverse=True)
        feature_addresses = surficial.address_point_df(feature_hits, edge_addresses)
        ax2.plot(
            feature_addresses['ds'], feature_addresses['z'],
            color=YELLOW, marker='o', linestyle='None', label='profile'
            )
    """
    if terrace_f:
        ax2.plot(
            point_addresses['ds'], point_addresses['z'],
            color=GREEN, marker='.', linestyle='None', alpha=0.5, label='profile'
            )
    """
    #ax2 = annotate_features(ax2, feature_addresses)

    ax2.invert_xaxis()
    ax2.set_aspect(100)

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
cli.add_command(network)
