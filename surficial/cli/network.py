import sys
import click
import fiona
from shapely.geometry import shape
from shapely import total_bounds
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib import colormaps

import surficial as srf
from surficial.tools.io import read_geometries
from surficial.tools.plotting import Extents, cols_to_linecollection, pad_extents


@click.command()
@click.argument('alignment', nargs=1, type=click.Path(exists=True))
@click.option('--show-spatial', is_flag=True, default=False,
              help="Network using spatial data")
@click.pass_context
def network(ctx, alignment, show_spatial):
    """Plots the network graph

    \b
    Example:
    surficial network stream_ln.shp

    """
    with fiona.open(alignment) as alignment_src:
        line_features = read_geometries(alignment_src)
        graph = srf.Alignment()
        graph.add_geometries(line_features)

    subgraphs = [
        graph.subgraph(c).copy() for c in nx.connected_components(graph.to_undirected())
        # graph.subgraph(c).copy() for c in nx.strongly_connected_components(graph)
    ]

    # plot
    fig = plt.figure()
    ax = fig.add_subplot(111)

    cmap = colormaps['tab10']

    if show_spatial:
        for i, subgraph in enumerate(subgraphs):

            style = {
                "color": cmap([i]),
                "linestyle": "-",
                "linewidth": 1.5,
                "label": "stream"
            }

            vertices = subgraph.get_vertices()
            edge_collection = cols_to_linecollection(vertices, xcol='x', ycol='y', style=style)
            ax.add_collection(edge_collection)

        minx, miny, maxx, maxy = total_bounds([line for _, line in line_features])
        extents = Extents(minx, miny, maxx, maxy)
        lims = pad_extents(extents, pad=0.05)
        unit='meter'
        ax.set(aspect=1,
               xlim=(lims.minx, lims.maxx), ylim=(lims.miny, lims.maxy),
               xlabel='Easting ({})'.format(unit.lower()),
               ylabel='Northing ({})'.format(unit.lower()))
    else:
        pos = nx.kamada_kawai_layout(graph)
        for i, subgraph in enumerate(subgraphs):
            nx.draw(subgraph, pos=pos, ax=ax, with_labels=True, node_color=cmap([i]))

    plt.show()
