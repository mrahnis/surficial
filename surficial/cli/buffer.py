import sys

import click
import fiona
from shapely.geometry import shape, mapping

import surficial as srf


@click.command()
@click.argument('alignment', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.argument('radius', nargs=1, type=click.FLOAT)
@click.option('-s', '--source', nargs=1, type=click.INT, help="Source node ID")
@click.option('-o', '--outlet', nargs=1, type=click.INT, help="Outlet node ID")
@click.pass_context
def buffer(ctx, alignment, output, radius, source, outlet):
    """
    Buffers a network graph or path within a network graph

    \b
    Example:
    surficial buffer stream_ln.shp buf.shp 100.0 -s 5

    """
    with fiona.open(alignment) as alignment_src:
        lines = [shape(line['geometry']) for line in alignment_src]
        source_driver = alignment_src.driver
        source_crs = alignment_src.crs

    # make the graph
    network = srf.Alignment(lines)

    if not outlet:
        outlet = network.outlet()
    if not source:
        path = network.edges()
    else:
        path = list(network.path_edges(source, outlet))
    buf = network.edge_buffer(radius, edges=path)

    sink_schema = {
        'geometry': 'Polygon',
        'properties': {'id': 'int'},
    }

    with fiona.open(
            output,
            'w',
            driver=source_driver,
            crs=source_crs,
            schema=sink_schema) as sink:
        sink.write({
            'geometry': mapping(buf),
            'properties': {'id': 0},
        })

    click.echo('Output written to: {}'.format(output))
