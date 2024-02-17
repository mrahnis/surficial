import click
import rasterio
import fiona
import matplotlib.pyplot as plt
from shapely.geometry import Point, LineString
from pyproj.crs import CRS
from adjustText import adjust_text

from drapery.ops.sample import sample
import surficial as srf
from surficial.tools import defaults, messages
from surficial.tools.io import read_geometries, read_crs, load_style
from surficial.tools.plotting import cols_to_linecollection, df_extents, pad_extents


LABEL_MESSAGE = "Label field {} not found in {}. Labeling with {}."


@click.command()
@click.argument('alignment', nargs=1, type=click.Path(exists=True))
@click.option('--surface', nargs=1, type=click.Path(exists=True))
@click.option('--points', 'point_layers', type=(click.Path(exists=True),
              click.STRING), multiple=True,
              help='Points to project onto profile using a given style')
@click.option('--style', nargs=1, type=click.Path(exists=True),
              help="JSON file containing plot styles")
@click.option('--label', nargs=1, type=click.STRING,
              help="Label point features with a given field")
@click.option('--despike/--no-despike', is_flag=True, default=True,
              help="Eliminate elevation up-spikes from the stream profile")
@click.option('--densify', nargs=1, type=click.FLOAT,
              help="Densify lines with regularly spaced stations")
@click.option('--radius', nargs=1, type=click.FLOAT, default=100.0, show_default=True,
              help="Search radius buffer for points")
@click.option('--invert/--no-invert', is_flag=True, default=True,
              help="Invert the x-axis")
@click.option('-e', '--exaggeration', nargs=1, type=click.INT, default=100, show_default=True,
              help="Vertical exaggeration of the profile")
@click.pass_context
def profile(ctx, alignment, surface, point_layers, style,
            label, despike, densify, radius, invert, exaggeration):
    """Plots a long profile

    \b
    Example:
    surficial profile stream_ln.shp --surface elevation.tif --points feature_pt.shp features --points terrace_pt.shp terrace --styles styles.json

    """

    with fiona.open(alignment) as alignment_src:
        base_crs = CRS.from_wkt(alignment_src.crs_wkt)
        if base_crs is not None and base_crs.is_projected:
            unit = (base_crs.axis_info)[0].unit_name
        else:
            raise click.BadParameter((messages.UNPROJECTED).format(alignment))

        line_features = read_geometries(alignment_src)

    if densify:
        line_features = [srf.densify_linestring(line_feature, step=densify) for line_feature in line_features]

    if surface:
        with rasterio.open(surface) as height_src:
            line_features = [(fid, LineString(sample(height_src, line.coords))) for fid, line in line_features]

    network = srf.Alignment(line_features)
    edge_addresses = network.edge_addresses(network.outlet())

    if despike:
        vertices = srf.core.alignment.remove_spikes(network)
    else:
        vertices = network.vertices

    # -----------
    # PLOTTING
    # -----------
    styles = defaults.styles.copy()
    if style:
        user_style = load_style(style)
        styles.update(user_style)

    texts = []
    handles = []
    fig = plt.figure()
    ax = fig.add_subplot(111)

    profile_lines = cols_to_linecollection(
        vertices, xcol='path_m', ycol='z', style=styles.get('alignment'))
    ax.add_collection(profile_lines)

    if despike:
        despiked_lines = cols_to_linecollection(
            vertices, xcol='path_m', ycol='zmin', style=styles.get('despiked'))
        ax.add_collection(despiked_lines)

    for point_layer, style_key in point_layers:
        with fiona.open(point_layer) as point_src:
            point_crs = CRS.from_wkt(point_src.crs_wkt) 
            if point_crs.equals(base_crs) is False:
                click.echo((messages.PROJECTION).format(point_layer, alignment))

            point_features = read_geometries(point_src)

            if point_src.schema['geometry'] != "3D Point":
                with rasterio.open(surface) as height_src:
                    point_features = [(fid, Point(sample(height_src, [(point.x, point.y)])))
                                   for fid, point in point_features]

            hits = srf.points_to_addresses(network, point_features, radius, reverse=False)
            addresses = srf.get_path_distances(hits, edge_addresses)

            if (style_key != 'terrace') and (label in (point_src.schema)['properties']):
                labels = [feature['properties'][label] for feature in point_src if feature.id in set(addresses['fid'])]

                _texts = [ax.text(m, z, lbl, clip_on=True, fontsize='small') for m, z, lbl
                          in zip(addresses['path_m'], addresses['z'], labels)]
                texts.extend(_texts)
            else:
                # default_field = (list(((point_src.schema)['properties']).keys()))[0]
                # click.echo((LABEL_MESSAGE).format(label, point_layer, default_field))
                # labels = [feature['properties'][default_field] for feature in point_src if feature.id in set(addresses['fid'])]
                pass


            # ---------------------------
            # TESTING A ROLLING STATISTIC
            # this fails if there is more than one segment because of the edge grouping in rolling_mean_edgewise
            '''
            if style_key == 'terrace':
                means = srf.rolling_mean_edgewise(addresses)
                terrace_lines = cols_to_linecollection(
                    means, xcol='path_m', ycol='zmean', style=styles.get('mean'))
                ax.add_collection(terrace_lines)
                handles.append(terrace_lines)

                srf.difference(vertices, means)
            '''

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

    extents = df_extents(vertices, xcol='path_m', ycol='z')
    lims = pad_extents(extents, pad=0.05)
    ax.set(aspect=exaggeration,
           xlim=(lims.minx, lims.maxx),
           ylim=(lims.miny, lims.maxy),
           xlabel='Distance ({})'.format(unit.lower()),
           ylabel='Elevation ({0}), {1}x v.e.'.format(unit.lower(), exaggeration))
    if invert:
        ax.invert_xaxis()
    if despike:
        handles.extend([profile_lines, despiked_lines])
    else:
        handles.extend([profile_lines])

    """

    if label:
        adjust_text(texts, vertices['path_m'], vertices['z'], ax=ax,
                    force_points=(0.0, 0.1), expand_points=(1.2, 1.2),
                    force_text=(0.0, 0.6), expand_text=(1.1, 1.4),
                    autoalign=False, only_move={'points': 'y', 'text': 'y'},
                    arrowprops=dict(arrowstyle="-", color='r', lw=0.5))
    """
    plt.legend(handles=handles)
    plt.show()
