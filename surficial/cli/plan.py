import click
import matplotlib.pyplot as plt
import pandas as pnd
import fiona
import numpy as np


import surficial as srf
from surficial.cli import defaults, util
import surficial.tools.messages as msg
from surficial.tools.plotting import cols_to_linecollection
from adjustText import adjust_text


@click.command()
@click.argument('alignment', nargs=1, type=click.Path(exists=True))
@click.option('--points', 'point_layers', type=(click.Path(exists=True), click.STRING), multiple=True,
              help='Plot points on the planview map using a given style')
@click.option('--style', 'style', nargs=1, type=click.Path(exists=True),
              help="JSON file containing plot styles")
@click.option('--label/--no-label', is_flag=True, default=False,
              help="Label features from a given field in the features dataset")
@click.option('--show-nodes/--hide-nodes', is_flag=True, default=False,
              help="Label network nodes in the alignment")
@click.pass_context
def plan(ctx, alignment, point_layers, style, label, show_nodes):
    """
    Plots a planview map

    \b
    Example:
    surficial plan stream_ln.shp --points terrace_pt.shp terrace --points feature_pt.shp features

    """
    _, alignment_crs, lines = util.read_geometries(alignment)
    base_crs, crs_status = util.check_crs(alignment_crs)
    if crs_status != 'success':
        raise click.BadParameter((msg.UNPROJECTED).format(alignment))
    unit = base_crs.GetAttrValue('unit')

    network = srf.Alignment(lines)
    vertices = network.vertices

    styles = defaults.styles.copy()
    if style:
        user_style = util.load_style(style)
        styles.update(user_style)

    texts = []
    handles = []
    fig = plt.figure()
    ax = fig.add_subplot(111)

    edge_collection = cols_to_linecollection(vertices, xcol='x', ycol='y', style=styles.get('despiked'))
    ax.add_collection(edge_collection)

    for point_layer, style_key in point_layers:
        _, point_crs, point_geoms = util.read_geometries(point_layer)

        _, crs_status = util.check_crs(point_crs, base_crs=base_crs)
        if crs_status != 'success':
            if crs_status == 'unprojected':
                raise click.BadParameter((msg.UNPROJECTED).format(point_layer))
            else:
                click.echo((msg.PROJECTION).format(point_layer, alignment))

        xx = [p.x for p in point_geoms]
        yy = [p.y for p in point_geoms]

        if 'left' and 'right' in styles.get(style_key):
            click.echo("Left and right styling not implemented in plan view; using left style only.")
            points, = ax.plot(xx, yy, **styles.get(style_key).get('left'))
        else:
            points, = ax.plot(xx, yy, **styles.get(style_key))
        handles.append(points)

        if label:
            with fiona.open(point_layer) as point_src:
                if 'LABEL' in (point_src.schema)['properties']:
                    labels = [feature['properties']['LABEL'] for feature in point_src]
                else:
                    labels = [feature['properties']['id'] for feature in point_src]
                _texts = [ax.text(x, y, tx, clip_on=True, fontsize='small') for x, y, tx
                          in zip(xx, yy, labels)]
            texts.extend(_texts)

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

    extents = util.df_extents(vertices, xcol='x', ycol='y')
    padx = (extents.maxx - extents.minx)*0.05
    pady = (extents.maxy - extents.miny)*0.05
    ax.set(aspect=1,
           xlim=(extents.minx - padx, extents.maxx + padx),
           ylim=(extents.miny - pady, extents.maxy + pady),
           xlabel='Easting ({})'.format(unit.lower()),
           ylabel='Northing ({})'.format(unit.lower()))

    if label:
        adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle="-", color='r', lw=0.5))

    plt.legend(handles=handles)
    plt.show()
