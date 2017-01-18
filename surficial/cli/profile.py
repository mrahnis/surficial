from collections import namedtuple

import click
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import pandas as pnd
import rasterio
from shapely.geometry import shape, Point, LineString

from drapery.ops.sample import sample
import surficial
from surficial.ops.shape import densify_linestring
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
@click.option('--densify', nargs=1, type=click.FLOAT, metavar='<float>',
              help="Densify lines with regularly spaced stations given a value for step in map units")
@click.option('--radius', nargs=1, type=click.FLOAT, default=100, metavar='<float>',
              help="Search radius buffer; points within the buffer will display in profile")
@click.option('--invert/--no-invert', is_flag=True, default=True,
              help="Invert the x-axis")
@click.option('-e', '--exaggeration', nargs=1, type=click.INT, default=100, metavar='<int>',
              help="Vertical exaggeration of the profile")
@click.pass_context
def profile(ctx, alignment_f, elevation_f, point_multi_f, styles_f, label, despike, densify, radius, invert, exaggeration):
    """
    Plots a long profile

    \b
    Example:
    surficial profile stream_ln.shp --surface elevation.tif --points feature_pt.shp features --points terrace_pt.shp terrace --styles styles.json

    """
    _, alignment_crs, lines = util.read_geometries(alignment_f)
    base_crs, crs_status = util.check_crs(alignment_crs)
    if crs_status != 'success':
        raise click.BadParameter('{} is {}'.format(alignment_f, crs_status))
    unit = base_crs.GetAttrValue('unit')

    if densify:
        lines = [densify_linestring(line, step=densify) for line in lines]

    if elevation_f:
        with rasterio.open(elevation_f) as elevation_src:
            lines = [LineString(sample(elevation_src, line.coords)) for line in lines]
        
    alignment = surficial.Alignment(lines)
    edge_addresses = alignment.edge_addresses(alignment.outlet())
    vertices = alignment.vertices()

    if despike:
        vertices = surficial.remove_spikes(vertices)

    # -----------
    # PLOTTING
    # -----------    
    styles = defaults.styles.copy()
    if styles_f:
        user_styles = util.load_style(styles_f)
        styles.update(user_styles)

    handles = []
    fig = plt.figure()
    ax = fig.add_subplot(111)

    profile_verts = [list(zip(edge['m'], edge['z'])) for _, edge in vertices.groupby(pnd.Grouper(key='edge'))]
    profile_lines = LineCollection(profile_verts, **styles.get('alignment'))
    ax.add_collection(profile_lines)

    if despike:
        despiked_verts = [list(zip(edge['m'], edge['zmin'])) for _, edge in vertices.groupby(pnd.Grouper(key='edge'))]
        despiked_lines = LineCollection(despiked_verts, **styles.get('despiked'))
        ax.add_collection(despiked_lines)
    for point_f, style_key in point_multi_f:
        point_type, point_crs, point_geoms = util.read_geometries(point_f)

        _, crs_status = util.check_crs(point_crs, base_crs=base_crs)
        if crs_status != 'success':
            if crs_status == 'unprojected':
                raise click.BadParameter('{} is unprojected'.format(point_f))
            else:
                msg = 'CRS of {} differs from the CRS of the alignment {}'.format(point_f, alignment_f)
                click.echo(msg)

        if point_type == 'Point':
            with rasterio.open(elevation_f) as elevation_src:
                point_geoms = [Point(sample(elevation_src, [(point.x, point.y)])) for point in point_geoms]
        elif point_type == '3D Point':
            point_geoms = [shape(point['geometry']) for point in point_geoms]
        hits = surficial.points_to_edge_addresses(alignment, point_geoms, radius=radius, reverse=True)

        # ---------------------------
        # TESTING A ROLLING STATISTIC        
        if style_key == 'terrace':
            hits_addresses = surficial.rebase_addresses(hits, edge_addresses)
            rolling_means = surficial.rolling_mean(hits_addresses)
            terrace_pts = [list(zip(edge.index.get_level_values('route_m'), edge['zmean'])) for _, edge in rolling_means.groupby(level=0)]
            terrace_lines = LineCollection(terrace_pts, **styles.get('line2'))
            ax.add_collection(terrace_lines)
            handles.append(terrace_lines)
        #----------------------------

        if 'left' and 'right' in styles.get(style_key):
            addresses_right = surficial.rebase_addresses(hits[(hits.d < 0)], edge_addresses)
            addresses_left = surficial.rebase_addresses(hits[(hits.d >= 0)], edge_addresses)
            points_left, = ax.plot(addresses_left['route_m'], addresses_left['z'], **styles.get(style_key).get('left'))
            points_right, = ax.plot(addresses_right['route_m'], addresses_right['z'], **styles.get(style_key).get('right'))
            handles.extend([points_left, points_right])        
        else:
            addresses = surficial.rebase_addresses(hits, edge_addresses)
            points, = ax.plot(addresses['route_m'], addresses['z'], **styles.get(style_key))
            handles.append(points)

    Extents = namedtuple('Extents', ['minx', 'miny', 'maxx', 'maxy']) 
    extents = Extents(vertices['m'].min(), vertices['z'].min(), vertices['m'].max(), vertices['z'].max())
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
