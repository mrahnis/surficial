import click
import fiona
from shapely.geometry import shape
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib import colormaps

import surficial as srf
from surficial.tools.io import read_geometries


@click.command()
@click.argument('alignment', nargs=1, type=click.Path(exists=True))
@click.pass_context
def network(ctx, alignment):
    """Plots the network graph

    \b
    Example:
    surficial network stream_ln.shp

    """
    with fiona.open(alignment) as alignment_src:
        line_features = read_geometries(alignment_src)
        graph = srf.Alignment(line_features)

    # plot
    fig = plt.figure()
    ax = fig.add_subplot(111)

    '''
    # would like to color subgraphs uniquely
    subgraphs = [
        graph.subgraph(c).copy() for c in nx.connected_components(graph.to_undirected())
        #graph.subgraph(c).copy() for c in nx.strongly_connected_components(graph)
    ]

    cmap = colormaps['tab10']
    for i, subgraph in enumerate(subgraphs):
        nx.draw(subgraph, ax=ax, node_color=cmap[i])
    '''

    nx.draw(graph, pos=nx.spring_layout(graph), ax=ax, with_labels=True, node_color='w')

    plt.show()
