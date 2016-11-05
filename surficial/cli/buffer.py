import sys

import click
import fiona
from shapely.geometry import shape, mapping

import surficial

@click.command(options_metavar='<options>')
@click.argument('alignment_f', nargs=1, type=click.Path(exists=True), metavar='<alignment_file>')
@click.argument('output_f', nargs=1, type=click.Path(), metavar='<output_file>')
@click.argument('radius', nargs=1, type=click.FLOAT, metavar='<float>')
@click.option('-s', '--source', nargs=1, type=click.INT, metavar='<int>', help="Source node ID")
@click.option('-o', '--outlet', nargs=1, type=click.INT, metavar='<int>', help="Outlet node ID")
@click.pass_context
def buffer(ctx, alignment_f, output_f, radius, source, outlet):
    """
    Buffers a network graph or path within a network graph

    \b
    Example:
    surficial buffer stream_ln.shp buf.shp 100.0 -s 5

    """
    with fiona.open(alignment_f) as alignment_src:
        lines = [shape(line['geometry']) for line in alignment_src]
        source_driver = alignment_src.driver
        source_crs = alignment_src.crs

    # make the graph
    alignment = surficial.Alignment(lines)

    if not outlet:
        outlet = alignment.outlet()
    if not source:
        path = alignment.edges()
    else:
        path = list(alignment.path_edges(source, outlet))
    buf = alignment.edge_buffer(radius, edges=path)

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

    click.echo('Output written to: {}'.format(output_f))
