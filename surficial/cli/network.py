import click
import fiona
from shapely.geometry import shape
import networkx as nx
import matplotlib.pyplot as plt

import surficial as srf


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
        lines = [shape(line['geometry']) for line in alignment_src]

    graph = srf.Alignment(lines)

    # plot
    fig = plt.figure()
    ax = fig.add_subplot(111)
    nx.draw(graph, ax=ax, with_labels=True, node_color='w')

    plt.show()
