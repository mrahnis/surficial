import click
import matplotlib.pyplot as plt
import fiona

import surficial as srf
from surficial.tools import defaults, messages
from surficial.tools.io import read_geometries, load_style
from surficial.tools.plotting import cols_to_linecollection, df_extents, pad_extents
from pyproj.crs import CRS
from adjustText import adjust_text


@click.command()
@click.argument('alignment', nargs=1, type=click.Path(exists=True))
@click.option('--points', 'point_layers', type=(click.Path(exists=True),
              click.STRING), multiple=True,
              help='Plot points on the planview map using a given style')
@click.option('--style', 'style', nargs=1, type=click.Path(exists=True),
              help="JSON file containing plot styles")
@click.option('--label', nargs=1, type=click.STRING,
              help="Label point features with a given field")
@click.option('--show-nodes/--hide-nodes', is_flag=True, default=False,
              help="Label network nodes in the alignment")
@click.pass_context
def plan(ctx, alignment, point_layers, style, label, show_nodes):
    """Plots a planview map

    \b
    Example:
    surficial plan stream_ln.shp --points terrace_pt.shp terrace --points feature_pt.shp features

    """

    with fiona.open(alignment) as alignment_src:
        base_crs = CRS.from_wkt(alignment_src.crs_wkt)
        if base_crs is not None and base_crs.is_projected:
            unit = (base_crs.axis_info)[0].unit_name
        else:
            raise click.BadParameter((messages.UNPROJECTED).format(alignment))

        line_features = read_geometries(alignment_src)

    network = srf.Alignment(line_features)
    vertices = network.get_vertices()

    styles = defaults.styles.copy()
    if style:
        user_style = load_style(style)
        styles.update(user_style)

    texts = []
    handles = []
    fig = plt.figure()
    ax = fig.add_subplot(111)

    edge_collection = cols_to_linecollection(vertices, xcol='x', ycol='y', style=styles.get('despiked'))
    ax.add_collection(edge_collection)

    for point_layer, style_key in point_layers:
        with fiona.open(point_layer) as point_src:
            point_crs = CRS.from_wkt(point_src.crs_wkt) 
            if point_crs.equals(base_crs) is False:
                click.echo((messages.PROJECTION).format(point_layer, alignment))

            point_features = read_geometries(point_src)

            xx = [p.x for _, p in point_features]
            yy = [p.y for _, p in point_features]

            if 'left' and 'right' in styles.get(style_key):
                # only going to use the left style here
                points, = ax.plot(xx, yy, **styles.get(style_key).get('left'))
            else:
                points, = ax.plot(xx, yy, **styles.get(style_key))
            handles.append(points)

            if (style_key != 'terrace') and (label in (point_src.schema)['properties']):
                labels = [feature['properties'][label] for feature in point_src]
                _texts = [ax.text(x, y, lbl, clip_on=True, fontsize='small') for x, y, lbl
                          in zip(xx, yy, labels)]
                texts.extend(_texts)
            else:
                # default_field = (list(((point_src.schema)['properties']).keys()))[0]
                # click.echo((LABEL_MESSAGE).format(label, point_layer, default_field))
                # labels = [feature['properties'][default_field] for feature in point_src if feature.id in set(addresses['fid'])]
                pass

    if show_nodes:
        nodes = network.nodes(data=True)
        node_labels = [node[0] for node in nodes]
        node_points = [node[1]['geom'] for node in nodes]
        node_x = [p.coords[0][0] for p in node_points]
        node_y = [p.coords[0][1] for p in node_points]
        for label, x, y in zip(node_labels, node_x, node_y):
            plt.annotate(
                label,
                xy=(x, y), xytext=(-20, 20),
                textcoords='offset points', ha='right', va='bottom',
                bbox=dict(boxstyle='round,pad=0.3', fc='yellow', alpha=0.5),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        nodes, = ax.plot(node_x, node_y, **styles.get('point1'))
        handles.append(nodes)

    handles.append(edge_collection)

    extents = df_extents(vertices, xcol='x', ycol='y')
    lims = pad_extents(extents, pad=0.05)
    ax.set(aspect=1,
           xlim=(lims.minx, lims.maxx), ylim=(lims.miny, lims.maxy),
           xlabel='Easting ({})'.format(unit.lower()),
           ylabel='Northing ({})'.format(unit.lower()))

    if label:
        adjust_text(texts, ax=ax,
                    arrowprops=dict(arrowstyle="-", color='r', lw=0.5))

    plt.legend(handles=handles)
    plt.show()
