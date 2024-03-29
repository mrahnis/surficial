import click
import fiona
from shapely.geometry import Point, shape, mapping

import surficial as srf
from surficial.tools import messages
from surficial.tools.io import read_geometries


@click.command()
@click.argument('alignment', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.argument('step', nargs=1, type=click.FLOAT)
@click.pass_context
def station(ctx, alignment, output, step):
    """Creates a series of evenly spaced stations

    \b
    Example:
    surficial station stream_ln.shp station_pt.shp 20

    """
    with fiona.open(alignment) as alignment_src:

        src_driver = alignment_src.driver
        src_crs = alignment_src.crs

        line_features = read_geometries(alignment_src)
        network = srf.Alignment()
        network.add_geometries(line_features)
        vertices = network.station(step)

    sink_schema = {
        'geometry': 'Point',
        'properties': {'id': 'int',
                       'station': 'float',
                       'from_node': 'int',
                       'to_node': 'int'},
    }

    with fiona.open(
            output,
            'w',
            driver=src_driver,
            crs=src_crs,
            schema=sink_schema) as sink:
        for i, row in vertices.iterrows():
            if row['z'] is not None:
                geom = Point(row['x'], row['y'], row['z'])
            else:
                geom = Point(row['x'], row['y'])
            # click.echo("Writing id: {}".format(i))
            sink.write({
                'geometry': mapping(geom),
                'properties': {'id': int(i),
                               'station': row['m'],
                               'from_node': row['edge'][0],
                               'to_node': row['edge'][1]}
            })
    click.echo((messages.OUTPUT).format(output))
