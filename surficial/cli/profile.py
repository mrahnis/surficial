import click
import matplotlib.pyplot as plt
import pandas as pnd
import rasterio
import fiona
from shapely.geometry import shape, Point, LineString
from adjustText import adjust_text

from drapery.ops.sample import sample
import surficial as srf
from surficial.cli import defaults, util
import surficial.tools.messages as msg
from surficial.tools.plotting import cols_to_linecollection


@click.command()
@click.argument('alignment', nargs=1, type=click.Path(exists=True))
@click.option('--surface', nargs=1, type=click.Path(exists=True))
@click.option('--points', 'point_layers', type=(click.Path(exists=True), click.STRING), multiple=True,
              help='Points to project onto profile using a given style')
@click.option('--style', nargs=1, type=click.Path(exists=True),
              help="JSON file containing plot styles")
@click.option('--label/--no-label', is_flag=True, default=False,
              help="Label features from a given field in the features dataset")
@click.option('--despike/--no-despike', is_flag=True, default=True,
              help="Eliminate elevation up-spikes from the stream profile")
@click.option('--densify', nargs=1, type=click.FLOAT,
              help="Densify lines with regularly spaced stations given a value for step in map units")
@click.option('--radius', nargs=1, type=click.FLOAT, default=100,
              help="Search radius buffer; points within the buffer will display in profile")
@click.option('--invert/--no-invert', is_flag=True, default=True,
              help="Invert the x-axis")
@click.option('-e', '--exaggeration', nargs=1, type=click.INT, default=100,
              help="Vertical exaggeration of the profile")
@click.pass_context
def profile(ctx, alignment, surface, point_layers, style, label, despike, densify, radius, invert, exaggeration):
    """
    Plots a long profile

    \b
    Example:
    surficial profile stream_ln.shp --surface elevation.tif --points feature_pt.shp features --points terrace_pt.shp terrace --styles styles.json

    """
    _, alignment_crs, lines = util.read_geometries(alignment)
    base_crs, crs_status = util.check_crs(alignment_crs)
    if crs_status != 'success':
        raise click.BadParameter((msg.UNPROJECTED).format(alignment))
    unit = base_crs.GetAttrValue('unit')

    if densify:
        lines = [srf.densify_linestring(line, step=densify) for line in lines]

    if surface:
        with rasterio.open(surface) as height_src:
            lines = [LineString(sample(height_src, line.coords)) for line in lines]

    network = srf.Alignment(lines)
    edge_addresses = network.edge_addresses(network.outlet())

    if despike:
        vertices = srf.remove_spikes(network)
    else:
        vertices = network.vertices

    # -----------
    # PLOTTING
    # -----------
    styles = defaults.styles.copy()
    if style:
        user_style = util.load_style(style)
        styles.update(user_style)

    texts = []
    handles = []
    fig = plt.figure()
    ax = fig.add_subplot(111)

    profile_lines = cols_to_linecollection(vertices, xcol='path_m', ycol='z', style=styles.get('alignment'))
    ax.add_collection(profile_lines)

    if despike:
        despiked_lines = cols_to_linecollection(vertices, xcol='path_m', ycol='zmin', style=styles.get('despiked'))
        ax.add_collection(despiked_lines)

    for point_layer, style_key in point_layers:
        point_type, point_crs, point_geoms = util.read_geometries(point_layer)

        _, crs_status = util.check_crs(point_crs, base_crs=base_crs)
        if crs_status != 'success':
            if crs_status == 'unprojected':
                raise click.BadParameter((msg.UNPROJECTED).format(point_layer))
            else:
                click.echo((msg.PROJECTION).format(point_layer, alignment))

        if point_geoms[0].has_z is False:
            with rasterio.open(surface) as height_src:
                point_geoms = [Point(sample(height_src, [(point.x, point.y)])) for point in point_geoms]
        hits = srf.points_to_addresses(network, point_geoms, radius=radius, reverse=False)
        addresses = srf.get_path_distances(hits, edge_addresses)

        if label:
            with fiona.open(point_layer) as point_src:
                if 'LABEL' in (point_src.schema)['properties']:
                    labels = [feature['properties']['LABEL'] for feature in point_src]
                else:
                    labels = [feature['properties']['id'] for feature in point_src]
                _texts = [ax.text(m, z, tx, clip_on=True, fontsize='small') for m, z, tx
                          in zip(addresses['path_m'], addresses['z'], labels)]
            texts.extend(_texts)

        # ---------------------------
        # TESTING A ROLLING STATISTIC
        if style_key == 'terrace':
            means = srf.rolling_mean_edgewise(addresses)
            terrace_lines = cols_to_linecollection(means, xcol='path_m', ycol='zmean', style=styles.get('mean'))
            ax.add_collection(terrace_lines)
            handles.append(terrace_lines)

            srf.difference(vertices, means)
        # ----------------------------
        # TEST ROLLING
        # srf.roll_down(network, 1, 2, 10)

        # ----------------------------
        # TEST EDGE_ADDRESS_TO_XYZ
        # location = srf.address_to_point(network, (5,0),100)
        # print(location)

        if 'left' and 'right' in styles.get(style_key):
            pts_left, = ax.plot(addresses['path_m'][(addresses.d >= 0)],
                                addresses['z'][(addresses.d >= 0)],
                                **styles.get(style_key).get('left'))
            pts_right, = ax.plot(addresses['path_m'][(addresses.d < 0)],
                                 addresses['z'][(addresses.d < 0)],
                                 **styles.get(style_key).get('right'))
            handles.extend([pts_left, pts_right])
        else:
            points, = ax.plot(addresses['path_m'], addresses['z'], **styles.get(style_key))
            handles.append(points)

    extents = util.df_extents(vertices, xcol='path_m', ycol='z')
    padx = (extents.maxx - extents.minx)*0.05
    pady = (extents.maxy - extents.miny)*0.05
    ax.set(aspect=exaggeration,
           xlim=(extents.minx - padx, extents.maxx + padx),
           ylim=(extents.miny - pady, extents.maxy + pady),
           xlabel='Distance ({})'.format(unit.lower()),
           ylabel='Elevation ({0}), {1}x v.e.'.format(unit.lower(), exaggeration))
    if invert:
        ax.invert_xaxis()
    if despike:
        handles.extend([profile_lines, despiked_lines])
    else:
        handles.extend([profile_lines])

    if label:
        adjust_text(texts, vertices['path_m'], vertices['z'], ax=ax,
                    force_points=(0.0, 0.1), expand_points=(1.2, 1.2),
                    force_text=(0.0, 0.6), expand_text=(1.1, 1.4),
                    autoalign=False, only_move={'points':'y', 'text':'y'},
                    arrowprops=dict(arrowstyle="-", color='r', lw=0.5))

    plt.legend(handles=handles)
    plt.show()
