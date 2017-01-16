import math
import bisect
from operator import itemgetter

from shapely.geometry import Point, LineString
from shapely.prepared import prep
import pandas as pnd

import surficial

def measure(line, start=0.0):
    """Return an array of vertex distances along a LineString.

    Parameters:
        line (LineString): the line on which to project.

    Other Parameters:
        start (float): measure at first vertex, zero by default.

    Returns:
        measures (list of float): list of vertex distances along line

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


def filter_contains(points, polygon):
    """Return a set of Points contained within a Polygon.

    Parameters:
        points (Point array): an array of Point to test.
        polygon (Polygon): the polygon to filter on.

    Returns:
        contained (list of Point): points contained within polygon

    """
    prepared_polygon = prep(polygon)
    contained = filter(prepared_polygon.contains, points)
    return contained


def project2d(point, line, measure=None):
    """Project a Point onto a line.

    Uses Shapely project(), which sets distance to zero for all negative distances.
    
    Note:
        The measure parameter does nothing at this time.
        I had intended to allow interpolation between measures other than distance.

    Parameters:
        point (Point): point at zero distance on line between point and p2.
        line (LineString): the line on which to project.

    Returns:
        result (dict): the projected Point, distance along line, offset from line.

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

    result = {'pt':pt, 'm':m, 'd':d}
    return result


def orient2d(point, projection, from_vert, to_vert):
    """Calculate the orientation and offset distance of a point from a line.

    Parameters:
        point (Point): point for which we want to determine orientation left or right of a line
        projection (Point): point of projection onto the line
        from_vert (Point): from point defining the line
        to_vert (Point): to point defining the line

    Returns:
        offset (float): point distance offset from the line; negative is left of the line, positive or zero is right of the line

    """
    if (point.y - from_vert.y) * (to_vert.x - from_vert.x) - (point.x - from_vert.x) * (to_vert.y - from_vert.y) < 0:
        offset = -point.distance(projection) # the point is offset left of the line
    else:
        offset = point.distance(projection) # the point is offset right of the line
    return offset

def linestring_to_vertices(line):
    """Return a list of [m,x,y,z] values for a LineString

    :m: measure of distance along the line from the first vertex
    :x: vertex x coordinate
    :y: vertex y coordinate
    :z: vertex z coordinate

    Parameters:
        line (LineString): shapely LineString

    Returns:
        vertices (list): list of [m,x,y,z] values  

    """
    vertices = []
    for p in list(line.coords):
        position = line.project(Point(p))
        if len(p) == 3:
            vertices.append([position, p[0], p[1], p[2]])
        else:
            vertices.append([position, p[0], p[1], None])
    return vertices

def linestring_to_stations(line, position=0.0, step=1.0):
    """Return a list of regularly spaced stations along a LineString

    Parameters:
        line (LineString): shapely LineString 

    Other Parameters:
        position (float): distance along the line from the first vertex; permits stationing to begin at some offset from the first vertex
        step (float): distance in-between stations along the line

    Returns:
        stations (list): list of [m,x,y,z] values

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

def densify_linestring(line, start=0, step=10):
    """Densify a LineString with regularly-spaced stations

    Parameters:
        line (LineString): shapely LineString

    Other Parameters:
        start (float): distance along the line from the first vertex; permits stationing to begin at some offset from the first vertex
        step (float): distance in-between stations along the line

    Returns:
        dense_line (LineString): densified line

    """
    vertices = linestring_to_vertices(line)
    stations = linestring_to_stations(line, position=start, step=step)
    dense_vertices = sorted(vertices + stations, key=itemgetter(0), reverse=False)
    if line.has_z:
        dense_line = LineString([Point(x[1], x[2], x[3]) for x in dense_vertices])
    else:
        dense_line = LineString([Point(x[1], x[2]) for x in dense_vertices])

    return dense_line

"""
def densify_linestring_alt(line, start=0, step=10):
    position = 0
    for vertex in vertices[1:]:
        how_far = p1.distance(p2)
        while how_far > 0:
           if position == 0:
               add the first vertex
           if position < start & start < how_far:
               make a start vertex
               position += start
               how_far -= start
           if how_far > step:
               make a step vertex
               position += step
               how_far -= step
           else:
               add next vertex
               position += how_far
               how_far = 0
    return dense_line
"""
