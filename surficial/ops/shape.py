from __future__ import annotations

from typing import Union
import math
import bisect
from operator import itemgetter

from shapely.geometry import Point, LineString, Polygon
from shapely.prepared import prep


def measure(line: LineString, start: float = 0.0) -> list[float]:
    """Return an array of vertex distances along a LineString

    Parameters:
        line: the line on which to project.

    Other Parameters:
        start: measure at first vertex, zero by default.

    Returns:
        measures as list of vertex distances along line

    """
    measures = []
    prev = (None, None)
    for i, vert in enumerate(line.coords):
        if i == 0:
            d = start
        else:
            d += math.sqrt((vert[0]-prev[0])**2 + (vert[1]-prev[1])**2)
        measures.append(d)
        prev = vert
    return measures


def filter_contains(points: list[Point], polygon: Polygon) -> list[Point]:
    """Return a set of Points contained within a Polygon

    Parameters:
        points: an array of Point to test.
        polygon: the polygon to filter on.

    Returns:
        Points contained within Polygon

    """
    prepared_polygon = prep(polygon)
    contained = filter(prepared_polygon.contains, points)
    return contained


def project2d(
    point: Point,
    line: LineString,
    measure: Union[None, str] = None
) -> dict:
    """Project a Point onto a line

    Uses Shapely project(), which sets distance to zero for all negative distances.

    Note:
        The measure parameter does nothing at this time.
        I had intended to allow interpolation between measures other than distance

    Parameters:
        point: point at zero distance on line between point and p2.
        line: the line on which to project.

    Returns:
        the projected Point, distance along line, offset from line

    """
    m = line.project(point, normalized=False)
    projected_2d = line.interpolate(m)
    pt = Point([projected_2d.x, projected_2d.y, point.z])

    # locate the segment where the projected point lies
    if measure is None:
        measure = measure(line)
    i = bisect.bisect_left(measure, m)
    # should check first and last to avoid out of index
    coords = list(line.coords)
    d = orient2d(point, pt, Point(coords[i]), Point(coords[i-1]))

    result = {'pt': pt, 'm': m, 'd': d}
    return result


def orient2d(
    point: Point,
    projection: Point,
    from_vert: Point,
    to_vert: Point
) -> float:
    """Calculate the orientation and offset distance of a point from a line

    Parameters:
        point: point for which we want to determine orientation left or right of a line
        projection: point of projection onto the line
        from_vert: from point defining the line
        to_vert: to point defining the line

    Returns:
        point distance offset from the line; negative is left of the line, positive or zero is right
        of the line

    """
    orientation = (point.y - from_vert.y) * (to_vert.x - from_vert.x) - \
                  (point.x - from_vert.x) * (to_vert.y - from_vert.y)
    if orientation < 0:
        offset = -point.distance(projection)  # point is offset left of line
    else:
        offset = point.distance(projection)  # point is offset right of line

    return offset


def linestring_to_vertices(line: LineString) -> list[list[float]]:
    """Return a list of [m,x,y,z] values for a LineString

    Parameters:
        line: shapely LineString

    Returns:
        list of vertex [m,x,y,z] values

        :m (float): measure of distance along the line from the first vertex
        :x (float): vertex x coordinate
        :y (float): vertex y coordinate
        :z (float): vertex z coordinate
    """
    vertices = []
    for p in list(line.coords):
        position = line.project(Point(p))
        if len(p) == 3:
            vertices.append([position, p[0], p[1], p[2]])
        else:
            vertices.append([position, p[0], p[1], None])
    return vertices


def linestring_to_stations(
    line: LineString,
    position: float = 0.0,
    step: Union[int, float] = 1.0
) -> list[list[float]]:
    """Return a list of regularly spaced stations along a LineString

    Parameters:
        line: shapely LineString

    Other Parameters:
        position: distance along the line from the first vertex; permits stationing to begin at some
            offset from the first vertex
        step: distance in-between stations along the line

    Returns:
        stations as list of [m,x,y,z] values

    """
    stations = []
    while position < line.length:
        p = line.interpolate(position)
        if p.has_z:
            stations.append([position, p.x, p.y, p.z])
        else:
            stations.append([position, p.x, p.y, None])
        position += step
    return stations


def densify_linestring(
    line: LineString,
    start: Union[int, float] = 0,
    step: Union[int, float] = 10
) -> LineString:
    """Densify a LineString with regularly-spaced stations

    Parameters:
        line: shapely LineString

    Other Parameters:
        start: distance along the line from the first vertex; permits stationing to begin at some
            offset from the first vertex
        step: distance in-between stations along the line

    Returns:
        densified line with new vertices spaced by the step distance

    """
    vertices = linestring_to_vertices(line)
    stations = linestring_to_stations(line, position=start, step=step)
    dense_vertices = sorted(vertices + stations, key=itemgetter(0), reverse=False)
    if line.has_z:
        dense_line = LineString([Point(x[1], x[2], x[3]) for x in dense_vertices])
    else:
        dense_line = LineString([Point(x[1], x[2]) for x in dense_vertices])

    return dense_line
