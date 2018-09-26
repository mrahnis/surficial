import sys

import click
import fiona
import rasterio
from shapely.geometry import Point, LineString, shape, mapping
from drapery.ops.sample import sample

import surficial


@click.command(options_metavar='<options>')
@click.argument('alignment_f', nargs=1, type=click.Path(exists=True), metavar='<alignment_file>')
@click.argument('output_f', nargs=1, type=click.Path(), metavar='<output_file>')
@click.option('--surface', 'elevation_f', nargs=1, type=click.Path(exists=True), metavar='<surface_file>')
@click.option('--densify', nargs=1, type=click.FLOAT, metavar='<float>',
              help="Densify lines with regularly spaced stations given a value for step in map units")
@click.option('--min-slope', 'min_slope', nargs=1, type=click.FLOAT, metavar='<float>',
              help="Minimum slope threshold in grade (rise/run)")
@click.option('--min-drop', 'min_drop', nargs=1, type=click.FLOAT, metavar='<float>',
              help="Minimum drop in elevation")
@click.option('--up/--down', 'up', default=True,
              help="Direction in which to accumulate drop")
@click.pass_context
def identify(ctx, alignment_f, output_f, elevation_f, densify, min_slope, min_drop, up):
    """
    Identifies locations that fit criteria

    \b
    Example:
    surficial identify stream_ln.shp feature_pt.shp dams --surface elevation.tif --min-slope 0.1

    """
    with fiona.open(alignment_f) as alignment_src:
        lines = [shape(line['geometry']) for line in alignment_src]
        source_driver = alignment_src.driver
        source_crs = alignment_src.crs
        source_schema = alignment_src.schema

    if densify:
        lines = [surficial.densify_linestring(line, step=densify) for line in lines]

    if elevation_f:
        with rasterio.open(elevation_f) as elevation_src:
            lines = [LineString(sample(elevation_src, line.coords)) for line in lines]

    alignment = surficial.Alignment(lines)

    despike = surficial.remove_spikes(alignment)
    alignment.vertices = despike
    vertices = surficial.slope(alignment, column='zmin')
    hits = surficial.knickpoint(vertices, min_slope, min_drop, up=up)

    print(hits)

    sink_schema = {
        'geometry': '3D Point',
        'properties': {'id': 'int', 'path_m': 'float', 'from_node': 'int', 'to_node': 'int', 'elevation': 'float', 'drop': 'float'},
    }

    with fiona.open(
            output_f,
            'w',
            driver=source_driver,
            crs=source_crs,
            schema=sink_schema) as sink:
        for i, row in hits.iterrows():
            if row['zmin'] is not None:
                geom = Point(row['x'], row['y'], row['zmin'])
            else:
                geom = Point(row['x'], row['y'])
            # click.echo("Writing id: {}".format(i))
            sink.write({
                'geometry': mapping(geom),
                'properties': {'id': int(i), 'path_m': row['path_m'], 'from_node': row['edge'][0], 'to_node': row['edge'][1], 'elevation': row['zmin'], 'drop': row['drop']}
            })
    click.echo('Wrote {0} features to: {1}'.format(len(hits.index), output_f))
