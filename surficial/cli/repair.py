import sys
import operator
from collections import Counter

import click
import fiona
from shapely.geometry import Point, LineString, shape, mapping

import surficial as srf


def scan(test_point, points, decimal):
    for point in points:
        if Point(test_point[2]).almost_equals(Point(point[2]), decimal=decimal):
            yield point


def edit_line(line, edits):
    edit_line_ids = [edit[0] for edit in edits]
    geom = shape(line[1])
    if line[0] in edit_line_ids:
        for edit in edits:
            if line[0] == edit[0]:
                # could pop the edit at this point
                click.echo("Snapping id {0}, {1}, to: {2}".format(edit[0], edit[1], edit[3]))
                coords = list(geom.coords)
                if edit[1] == 'start':
                    geom = LineString([edit[3]] + coords[1:])
                elif edit[1] == 'end':
                    geom = LineString(coords[:-1] + [edit[3]])
                else:
                    click.echo("Snap operation must be on start or end point")
    return geom


@click.command()
@click.argument('alignment', nargs=1, type=click.Path(exists=True))
@click.option('-o', '--output', nargs=1, type=click.Path(),
              help="Output file")
@click.option('-d', '--decimal', nargs=1, type=click.INT, default=6,
              help="Decimal place precision")
@click.pass_context
def repair(ctx, alignment, output, decimal):
    """
    Closes gaps in a network graph

    \b
    Example:
    surficial repair stream_ln.shp stream_ln_snap.shp --decimal 4

    """
    with fiona.open(alignment) as alignment_src:
        lines = [[line['id'], shape(line['geometry']), line['properties']]
                 for line in alignment_src]
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

    # compile edits to snap endpoints to the most frequently occurring
    # endpoint within a cluster of endpoints
    edits = []
    for cluster in clusters:
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
    if output:
        with fiona.open(
                output,
                'w',
                driver=source_driver,
                crs=source_crs,
                schema=source_schema) as sink:
            for line in lines:
                geom = edit_line(line, edits)
                sink.write({
                    'geometry': mapping(geom),
                    'properties': line[2],
                })
        click.echo('Completed, output written to: {}'.format(output))
    else:
        click.echo('No output file given, starting dry-run')
        for line in lines:
            edit_line(line, edits)
        click.echo('Completed')
