from collections import namedtuple

import click
from gdal import osr
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import pandas as pnd

import drapery
import surficial
from surficial.cli import defaults, util


@click.command(options_metavar='<options>')
@click.argument('alignment_f', nargs=1, type=click.Path(exists=True), metavar='<alignment_file>')
@click.option('--surface', 'elevation_f', nargs=1, type=click.Path(exists=True), metavar='<surface_file>')
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
@click.pass_context
def profile(ctx, alignment_f, elevation_f, point_multi_f, styles_f, label, despike, station, invert, exaggeration):
    """
    Plots a long profile

    \b
    Example:
    surficial profile stream_ln.shp elevation.tif --points feature_pt.shp features --points terrace_pt.shp terrace --styles styles.json

    """
    alignment_crs, lines = util.read_geometries(alignment_f, elevation_f=elevation_f)
    crs=osr.SpatialReference(wkt=alignment_crs)
    if crs.IsProjected:
        unit = crs.GetAttrValue('unit')
    else:
        raise click.BadParameter('Data are not projected')

    # Alignment creation, and draping is done here, prior to stationing
    alignment = surficial.Alignment(lines)

    edge_addresses = alignment.edge_addresses(alignment.outlet())

    if station:
        # Densifying or stationing here will not resample elevation 
        vertices = alignment.station(station, keep_vertices=True)
    else:
        vertices = alignment.vertices()

    Extents = namedtuple('Extents', ['minx', 'miny', 'maxx', 'maxy']) 
    extents = Extents(vertices['s'].min(), vertices['z'].min(), vertices['s'].max(), vertices['z'].max())

    if despike:
        vertices = surficial.remove_spikes(vertices)

    styles = defaults.styles.copy()
    if styles_f:
        user_styles = util.load_style(styles_f)
        styles.update(user_styles)

    handles = []
    fig = plt.figure()
    ax = fig.add_subplot(111)

    profile_verts = [list(zip(edge_verts['s'], edge_verts['z'])) for _, edge_verts in vertices.groupby(pnd.Grouper(key='edge'))]
    profile_lines = LineCollection(profile_verts, **styles.get('alignment'))
    ax.add_collection(profile_lines)

    if despike:
        despiked_verts = [list(zip(edge_verts['s'], edge_verts['zmin'])) for _, edge_verts in vertices.groupby(pnd.Grouper(key='edge'))]
        despiked_lines = LineCollection(despiked_verts, **styles.get('despiked'))
        ax.add_collection(despiked_lines)
    for point_f, style_key in point_multi_f:
        _, point_geoms = util.read_geometries(point_f, elevation_f=elevation_f)
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

    padx = (extents.maxx - extents.minx)*0.05
    pady = (extents.maxy - extents.miny)*0.05
    ax.set(aspect=exaggeration,
           xlim=(extents.minx - padx, extents.maxx + padx),
           ylim=(extents.miny - pady, extents.maxy + pady),
           xlabel='Distance ({})'.format(unit.lower()),
           ylabel='Elevation ({0}), {1}x v.e.'.format(unit.lower(), exaggeration))
    if invert:
        ax.invert_xaxis()
    handles.extend([profile_lines, despiked_lines])
    plt.legend(handles=handles)
    plt.show()


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
