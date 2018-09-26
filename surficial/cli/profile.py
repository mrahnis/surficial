import click
import matplotlib.pyplot as plt
import pandas as pnd
import rasterio
import fiona
from shapely.geometry import shape, Point, LineString
from adjustText import adjust_text

from drapery.ops.sample import sample
import surficial
from surficial.cli import defaults, util
import surficial.tools.messages as msg
from surficial.tools.plotting import vertices_to_linecollection


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
        raise click.BadParameter((msg.UNPROJECTED).format(alignment_f))
    unit = base_crs.GetAttrValue('unit')

    if densify:
        lines = [surficial.densify_linestring(line, step=densify) for line in lines]

    if elevation_f:
        with rasterio.open(elevation_f) as elevation_src:
            lines = [LineString(sample(elevation_src, line.coords)) for line in lines]

    alignment = surficial.Alignment(lines)
    edge_addresses = alignment.edge_addresses(alignment.outlet())

    if despike:
        vertices = surficial.remove_spikes(alignment)
    else:
        vertices = alignment.vertices

    # -----------
    # PLOTTING
    # -----------
    styles = defaults.styles.copy()
    if styles_f:
        user_styles = util.load_style(styles_f)
        styles.update(user_styles)

    texts = []
    handles = []
    fig = plt.figure()
    ax = fig.add_subplot(111)

    profile_lines = vertices_to_linecollection(vertices, xcol='m_relative', ycol='z', style=styles.get('alignment'))
    ax.add_collection(profile_lines)

    if despike:
        despiked_lines = vertices_to_linecollection(vertices, xcol='m_relative', ycol='zmin', style=styles.get('despiked'))
        ax.add_collection(despiked_lines)

    for point_f, style_key in point_multi_f:
        point_type, point_crs, point_geoms = util.read_geometries(point_f)

        _, crs_status = util.check_crs(point_crs, base_crs=base_crs)
        if crs_status != 'success':
            if crs_status == 'unprojected':
                raise click.BadParameter((msg.UNPROJECTED).format(point_f))
            else:
                click.echo((msg.PROJECTION).format(point_f, alignment_f))

        if point_geoms[0].has_z is False:
            with rasterio.open(elevation_f) as elevation_src:
                point_geoms = [Point(sample(elevation_src, [(point.x, point.y)])) for point in point_geoms]
        hits = surficial.points_to_edge_addresses(alignment, point_geoms, radius=radius, reverse=False)
        addresses = surficial.rebase_addresses(hits, edge_addresses)

        if label:
            with fiona.open(point_f) as feature_src:
                if 'LABEL' in (feature_src.schema)['properties']:
                    labels = [feature['properties']['LABEL'] for feature in feature_src]
                else:
                    labels = [feature['properties']['id'] for feature in feature_src]
                _texts = [ax.text(m, z, tx, clip_on=True, fontsize='small') for m, z, tx
                          in zip(addresses['m_relative'], addresses['z'], labels)]
            texts.extend(_texts)

        # ---------------------------
        # TESTING A ROLLING STATISTIC
        if style_key == 'terrace':
            means = surficial.rolling_mean_edgewise(addresses)
            terrace_lines = vertices_to_linecollection(means, xcol='m_relative', ycol='zmean', style=styles.get('mean'))
            ax.add_collection(terrace_lines)
            handles.append(terrace_lines)

            surficial.difference(vertices, means)
        # ----------------------------
        # TEST ROLLING
        # surficial.roll_down(alignment, 1, 2, 10)

        # ----------------------------
        # TEST EDGE_ADDRESS_TO_XYZ
        # location = surficial.edge_address_to_point(alignment, (5,0),100)
        # print(location)

        if 'left' and 'right' in styles.get(style_key):
            pts_left, = ax.plot(addresses['m_relative'][(addresses.d >= 0)], addresses['z'][(addresses.d >= 0)], **styles.get(style_key).get('left'))
            pts_right, = ax.plot(addresses['m_relative'][(addresses.d < 0)], addresses['z'][(addresses.d < 0)], **styles.get(style_key).get('right'))
            handles.extend([pts_left, pts_right])
        else:
            points, = ax.plot(addresses['m_relative'], addresses['z'], **styles.get(style_key))
            handles.append(points)

    extents = util.df_extents(vertices, xcol='m_relative', ycol='z')
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
        iters = adjust_text(texts, vertices['m_relative'], vertices['z'], ax=ax,
                            force_points=(0.0, 0.1), expand_points=(1.2, 1.2),
                            force_text=(0.0, 0.6), expand_text=(1.1, 1.4),
                            autoalign=False, only_move={'points':'y', 'text':'y'},
                            arrowprops=dict(arrowstyle="-", color='r', lw=0.5))
        print(iters, 'iterations')

    plt.legend(handles=handles)
    plt.show()
