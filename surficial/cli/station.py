import sys

import click
import fiona
from shapely.geometry import Point, LineString, shape, mapping

import surficial


@click.command(options_metavar='<options>')
@click.argument('alignment_f', nargs=1, type=click.Path(exists=True), metavar='<alignment_file>')
@click.argument('output_f', nargs=1, type=click.Path(), metavar='<output_file>')
@click.argument('step', nargs=1, type=click.INT, metavar='<int>')
@click.pass_context
def station(ctx, alignment_f, output_f, step):
    """
    Creates a series of evenly spaced stations

    \b
    Example:
    surficial station stream_ln.shp station_pt.shp 20

    """
    with fiona.open(alignment_f) as alignment_src:
        lines = [shape(line['geometry']) for line in alignment_src]
        source_driver = alignment_src.driver
        source_crs = alignment_src.crs
        source_schema = alignment_src.schema

        alignment = surficial.Alignment(lines)

        vertices = alignment.station(step, keep_vertices=False)
        print(vertices.head())

    """
    with fiona.open(
        output_f,
        'w',
        driver=source_driver,
        crs=source_crs,
        schema=source_schema) as sink:

            click.echo("Writing id: {}".format(line[0]))
            sink.write({
                'geometry': mapping(geom),
                'properties': line[2],
            })
    click.echo('Output written to: {}'.format(output_f))
    """
