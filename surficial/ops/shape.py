import math
import bisect
from shapely.geometry import Point
from shapely.prepared import prep
import pandas as pnd

#from surficial.ops.graph import get_outlet, get_path_weight, get_path_edges
import surficial

def measure(line, start=0.0):
    """Return an array of vertex distances along a LineString.

    Parameters:
        line (LineString): the line on which to project.
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
    """Project a Point, point onto a line.

    Uses Shapely project(), which sets distance to zero for all negative distances.

    Parameters:
        point (Point): point at zero distance on line between point and p2.
        line (LineString): the line on which to project.

    Returns:
        result (dict): the projected Point, distance along line, offset from line.

    """
    d = line.project(point, normalized=False)
    projected_2d = line.interpolate(d)
    pt = Point([projected_2d.x, projected_2d.y, point.z])

    # locate the segment where the projected point lies
    if measure is None:
        measure = measure(line)
    i = bisect.bisect_left(measure, d)
    # should check first and last to avoid out of index
    coords = list(line.coords)
    offset = orient2d(point, pt, Point(coords[i]), Point(coords[i-1]))

    result = {'pt':pt, 'd':d, 'o':offset}
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

