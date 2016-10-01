import math
import bisect
from shapely.geometry import Point
from shapely.prepared import prep
import pandas as pnd

#from surficial.ops.graph import get_outlet, get_path_weight, get_path_edges
import surficial

def measure_verts(line, start=0.0):
    """
    Return an array of vertex distances along a LineString.

    Parameters
    ----------
    line (LineString) : the line on which to project.
    start (float) : measure at first vertex, zero by default.

    Returns
    -------
    measures : array of float.

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


def filter_points(points, polygon):
    """
    Return a set of Points contained within a Polygon.

    Parameters
    ----------
    points (Point array) : an array of Point to test.
    polygon (Polygon) : the polygon to filter on.

    Returns
    -------
    contained : array of Point.

    """
    prepared_polygon = prep(polygon)
    contained = filter(prepared_polygon.contains, points)
    return contained


def project_point_onto_line(point, line, measure=None):
    """
    Project a Point, point onto a line.
    Uses Shapely project(), which sets distance to zero for all negative distances.

    Parameters
    ----------
    point (Point) : point at zero distance on line between point and p2.
    line (LineString) : the line on which to project.

    Returns
    -------
    result (dict) : the projected Point, distance along line, offset from line.

    """
    d = line.project(point, normalized=False)
    projected_2d = line.interpolate(d)
    pt = Point([projected_2d.x, projected_2d.y, point.z])

    # locate the segment where the projected point lies
    if measure is None:
        measure = measure_verts(line)
    i = bisect.bisect_left(measure, d)
    # should check first and last to avoid out of index
    coords = list(line.coords)
    offset = orient2d(point, pt, Point(coords[i]), Point(coords[i-1]))

    result = {'pt':pt, 'd':d, 'o':offset}
    return result


def orient2d(point, projection, from_vert, to_vert):
    """
    Calculate the orientation and offset distance of a point from a line.

    Parameters
    ----------
    point (Point)
    projection (Point)
    from_vert (Point)
    to_vert (Point)

    Returns
    -------
    offset (float)

    """
    if (point.y - from_vert.y) * (to_vert.x - from_vert.x) - (point.x - from_vert.x) * (to_vert.y - from_vert.y) < 0:
        offset = -point.distance(projection) # the point is offset left of the line
    else:
        offset = point.distance(projection) # the point is offset right of the line
    return offset


def station(graph, step, keep_vertices=False):
    """
    Get a dataframe of regularly spaced stations along graph edges with zero at the start of each graph edge.

    \b
    To improve it needs to regularly space them throughout the network starting from the outlet by tracking the remainder at each edge.

    Parameters
    ----------
    g (DiGraph)
    step (float)
    keep-vertices (boolean)

    Returns
    -------
    stations (DataFrame)

    """
    from operator import itemgetter

    outlet = surficial.get_outlet(graph)

    stations = pnd.DataFrame()
    for u, v, data in graph.edges(data=True):
        # get the distance from the downstream node to the
        path = surficial.get_path_edges(graph, u, outlet)
        path_len = surficial.get_path_weight(graph, path, 'len')
        line = data['geom']

        ''' maybe change while statement to for statement below for clarity'''
        # calculate the stations
        stations_tmp = []
        d = 0
        while d < line.length:
            s = path_len - d
            p = line.interpolate(d)
            if p.has_z:
                stations_tmp.append([s, p.x, p.y, p.z, (u, v)])
            else:
                stations_tmp.append([s, p.x, p.y, None, (u, v)])
            d += step
        # get the vertices
        if keep_vertices:
            for p in list(line.coords):
                d = line.project(Point(p))
                s = path_len - d
                if len(p) == 3:
                    stations_tmp.append([s, p[0], p[1], p[2], (u, v)])
                else:
                    stations_tmp.append([s, p[0], p[1], None, (u, v)])
            stations_tmp = sorted(stations_tmp, key=itemgetter(0), reverse=True)
        if stations.empty:
            stations = pnd.DataFrame(stations_tmp, columns=['s', 'x', 'y', 'z', 'edge'])
        else:
            stations = pnd.concat([
                stations,
                pnd.DataFrame(stations_tmp, columns=['s', 'x', 'y', 'z', 'edge'])
                ], ignore_index=True)
    return stations
