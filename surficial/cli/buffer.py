import sys
import logging

import fiona
from shapely.geometry import shape, mapping
import click

import surficial

@click.command()
@click.argument('stream_f', nargs=1, type=click.Path(exists=True), metavar='<stream_file>')
@click.argument('output_f', nargs=1, type=click.Path(), metavar='<output_file>')
@click.argument('distance', nargs=1, type=click.FLOAT, metavar='<float>')
@click.option('-s', '--source', nargs=1, type=click.INT, metavar='<int>', help="Source node ID")
@click.option('-o', '--outlet', nargs=1, type=click.INT, metavar='<int>', help="Outlet node ID")
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode')
def cli(stream_f, output_f, distance, source, outlet, verbose):
    """
    Buffers a network graph or path within a network graph

    \b
    Example:
    buffer stream_ln.shp buf.shp 100.0 -s 5
    """

    if verbose is True:
        loglevel = 2
    else:
        loglevel = 0

    logging.basicConfig(stream=sys.stderr, level=loglevel or logging.INFO)
    logger = logging.getLogger('surficial')

    # stream
    with fiona.open(stream_f) as stream_src:
        lines = [shape(line['geometry']) for line in stream_src]
        source_driver = stream_src.driver
        source_crs = stream_src.crs

    # make the graph
    graph = surficial.construct(lines)

    if not outlet:
        outlet = surficial.get_outlet(graph)
    if not source:
        path = graph.edges()
    else:
        path = list(surficial.get_path_edges(graph, source, outlet))
    buf = surficial.get_edge_buffer(graph, distance, edges=path)

    sink_schema = {
        'geometry': 'Polygon',
        'properties': {'id': 'int'},
    }

    with fiona.open(
        output_f,
        'w',
        driver=source_driver,
        crs=source_crs,
        schema=sink_schema) as sink:
        sink.write({
           	'geometry': mapping(buf),
           	'properties': {'id': 0},
        })

    logger.info('Output written to: {}'.format(output_f))
