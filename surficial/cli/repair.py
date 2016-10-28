import sys

import fiona
from shapely.geometry import Point, LineString, shape, mapping
import click

import surficial

def scan(test_point, points, decimal):
    for point in points:
        if Point(test_point[2]).almost_equals(Point(point[2]), decimal=decimal):
            yield point

@click.command(options_metavar='<options>')
@click.argument('alignment_f', nargs=1, type=click.Path(exists=True), metavar='<alignment_file>')
@click.argument('output_f', nargs=1, type=click.Path(), metavar='<output_file>')
@click.option('-d', '--decimal', nargs=1, type=click.INT, metavar='<int>', default=6, help="Decimal place precision")
def cli(alignment_f, output_f, decimal):
    """
    Closes gaps in a network graph

    \b
    Example:
    repair stream_ln.shp stream_ln_snap.shp --decimal 4

    """
    with fiona.open(alignment_f) as alignment_src:
        lines = [[line['id'], shape(line['geometry']), line['properties']] for line in alignment_src]
        source_driver = alignment_src.driver
        source_crs = alignment_src.crs
        source_schema = alignment_src.schema

    # make a list of [id, start/end, coords]
    endpoints = []
    for line in lines:
        endpoints.append([line[0], 'start', line[1].coords[0]])
        endpoints.append([line[0], 'end', line[1].coords[-1]])

    # find clusters endpoints to a decimal place precision
    clusters = []
    while endpoints:
        test_point = endpoints.pop(0)
        near_points = list(scan(test_point, endpoints, decimal))
        if len(near_points) > 0:
            # could broaden search by scanning each near_point but
            # just trying to fix failed snap points so pop the near_points
            cluster = [test_point] + near_points
            clusters.append(cluster)
            for i, point in enumerate(endpoints):
                if point in near_points:
                    endpoints.pop(i)

    # compile edits to snap endpoints to the most frequently occurring within a cluster
    edits = []
    for cluster in clusters:
        from collections import Counter
        import operator

        coords = [endpoint[2] for endpoint in cluster]
        keys = list(Counter(coords).keys())
        values = list(Counter(coords).values())
        index, value = max(enumerate(values), key=operator.itemgetter(1))
        snap_point = keys[index]

        for endpoint in cluster:
            if endpoint[2] != snap_point:
                edit = endpoint[:]
                edit.append(snap_point)
                edits.append(edit)

    # make the edits while writing out the data
    with fiona.open(
        output_f,
        'w',
        driver=source_driver,
        crs=source_crs,
        schema=source_schema) as sink:
            edit_line_ids = [edit[0] for edit in edits]
            for line in lines:
                geom = shape(line[1])
                if line[0] in edit_line_ids:
                    for edit in edits:
                        if line[0] == edit[0]:
                            # could pop the edit at this point
                            click.echo("Snapping id {}, {} to: {}".format(edit[0], edit[1], edit[3]))
                            coords = list(geom.coords)
                            if edit[1] == 'start':
                                geom = Linestring([edit[3]] + coords[1:])
                            elif edit[1] == 'end':
                                geom = LineString(coords[:-1] + [edit[3]])
                            else:
                                print("snap operation must be on start or end point")
                click.echo("Writing id: {}".format(line[0]))
                sink.write({
                    'geometry': mapping(geom),
                    'properties': line[2],
                })
    click.echo('Output written to: {}'.format(output_f))
