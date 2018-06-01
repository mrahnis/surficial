import click
import matplotlib.pyplot as plt
import pandas as pnd

import surficial
from surficial.cli import defaults, util
from surficial.tools.plotting import vertices_to_linecollection


@click.command(options_metavar='<options>')
@click.argument('alignment_f', nargs=1, type=click.Path(exists=True), metavar='<alignment_file>')
@click.option('--points', 'point_multi_f', type=(click.Path(exists=True), click.STRING), multiple=True, metavar='<point_file> <style>',
              help='Plot points on the planview map using a given style')
@click.option('--styles', 'styles_f', nargs=1, type=click.Path(exists=True), metavar='<styles_file>',
              help="JSON file containing plot styles")
@click.option('--show-nodes/--hide-nodes', is_flag=True, default=False,
              help="Label network nodes in the alignment")
@click.pass_context
def plan(ctx, alignment_f, point_multi_f, styles_f, show_nodes):
    """
    Plots a planview map

    \b
    Example:
    surficial plan stream_ln.shp --points terrace_pt.shp terrace --points feature_pt.shp features

    """
    _, alignment_crs, lines = util.read_geometries(alignment_f)
    base_crs, crs_status = util.check_crs(alignment_crs)
    if crs_status != 'success':
        raise click.BadParameter('{} is {}'.format(alignment_f, crs_status))
    unit = base_crs.GetAttrValue('unit')

    alignment = surficial.Alignment(lines)
    vertices = alignment.vertices

    styles = defaults.styles.copy()
    if styles_f:
        user_styles = util.load_style(styles_f)
        styles.update(user_styles)

    handles = []
    fig = plt.figure()
    ax = fig.add_subplot(111)

    edge_collection = vertices_to_linecollection(vertices, xcol='x', ycol='y', style=styles.get('despiked'))
    ax.add_collection(edge_collection)

    for point_f, style_key in point_multi_f:
        _, point_crs, point_geoms = util.read_geometries(point_f)

        _, crs_status = util.check_crs(point_crs, base_crs=base_crs)
        if crs_status != 'success':
            if crs_status == 'unprojected':
                raise click.BadParameter('{} is unprojected'.format(point_f))
            else:
                msg = 'CRS of {} differs from the CRS of the alignment {}'.format(point_f, alignment_f)
                click.echo(msg)

        if 'left' and 'right' in styles.get(style_key):
            click.echo("Left and right styling not implemented in plan view; using left style only.")
            points, = ax.plot([p.coords.xy[0] for p in point_geoms], [p.coords.xy[1] for p in point_geoms], **styles.get(style_key).get('left'))
        else:
            points, = ax.plot([p.coords.xy[0] for p in point_geoms], [p.coords.xy[1] for p in point_geoms], **styles.get(style_key))
        handles.append(points)

    if show_nodes:
        nodes = alignment.nodes(data=True)
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
    plt.legend(handles=handles)
    plt.show()
