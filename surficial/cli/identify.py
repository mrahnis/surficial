import click
import fiona
import rasterio
from shapely.geometry import Point, LineString, shape, mapping
from drapery.ops.sample import sample

import surficial as srf
from surficial.tools import messages


@click.command()
@click.argument('alignment', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.option('--surface', nargs=1, type=click.Path(exists=True))
@click.option('--densify', nargs=1, type=click.FLOAT,
              help="Densify lines with regularly spaced stations")
@click.option('--min-slope', 'min_slope', nargs=1, type=click.FLOAT,
              help="Minimum slope threshold in grade (rise/run)")
@click.option('--min-drop', 'min_drop', nargs=1, type=click.FLOAT,
              help="Minimum drop in elevation")
@click.option('--up/--down', 'up', default=True,
              help="Direction in which to accumulate drop")
@click.pass_context
def identify(ctx, alignment, output, surface, densify, min_slope, min_drop, up):
    """Identifies locations that fit criteria

    \b
    Example:
    surficial identify stream_ln.shp feature_pt.shp dams --surface elevation.tif --min-slope 0.1

    """
    with fiona.open(alignment) as alignment_src:
        lines = [shape(line['geometry']) for line in alignment_src]
        source_driver = alignment_src.driver
        source_crs = alignment_src.crs
        source_schema = alignment_src.schema

    if densify:
        lines = [srf.densify_linestring(line, step=densify) for line in lines]

    if surface:
        with rasterio.open(surface) as height_src:
            lines = [LineString(sample(height_src, line.coords)) for line in lines]

    network = srf.Alignment(lines)

    despike = srf.remove_spikes(network)
    network.vertices = despike
    vertices = srf.slope(network, column='zmin')
    hits = srf.knickpoint(vertices, min_slope, min_drop, up=up)

    sink_schema = {
        'geometry': '3D Point',
        'properties': {'id': 'int',
                       'path_m': 'float',
                       'from_node': 'int',
                       'to_node': 'int',
                       'elevation': 'float',
                       'drop': 'float'},
    }

    with fiona.open(
            output,
            'w',
            driver=source_driver,
            crs=source_crs,
            schema=sink_schema) as sink:
        for i, row in hits.iterrows():
            if row['zmin'] is not None:
                geom = Point(row['x'], row['y'], row['zmin'])
            else:
                geom = Point(row['x'], row['y'])

            sink.write({
                'geometry': mapping(geom),
                'properties': {'id': int(i),
                               'path_m': row['path_m'],
                               'from_node': row['edge'][0],
                               'to_node': row['edge'][1],
                               'elevation': row['zmin'],
                               'drop': row['drop']}
            })

    click.echo((messages.FEATURECOUNT).format(len(hits.index), 'candidate dams'))
    click.echo((messages.OUTPUT).format(output))
