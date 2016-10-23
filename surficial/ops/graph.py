import networkx as nx
from shapely.geometry import Point, MultiLineString
import pandas as pnd

from surficial.ops.shape import measure, filter_contains, project2d

def points_to_edge_addresses(graph, points, distance=100, edges=None, reverse=False):
    """Locate points by address along the nearest graph edge.

    Returns a DataFrame describing the addresses (projections) of points, within some distance, onto a set of graph edges.
    The DataFrame columns are:

        :s (float): distance along the edge geometry
        :x (float): projected point x coordinate
        :y (float): projected point y coordinate
        :z (float): projected point z coordinate
        :d (float): offset distance, or distance from the point to its projection
        :edge (tuple): tuple of node identifiers identifying an edge 

    Parameters:
        graph (DiGraph): directed network graph
        points (list of Points): points to project

    Other Parameters:
        distance (float): buffer radius
        edges (list of tuples): edge tuples onto which points will be projected, if None then all edges in graph are used
        reverse (bool): reverse vertex ordering

    Returns:
        rows_df (DataFrame): point address information relative to individual edges

    """
    if edges is None:
        edges = graph.edges()
        
    rows = []
    for edge in edges:
        buffer = graph.edge_buffer(distance, edges=[edge])
        pts = filter_contains(points, buffer)
        geom = graph[edge[0]][edge[1]]['geom']
        meas = graph[edge[0]][edge[1]]['meas']
        for p in pts:
            pp = project2d(p, geom, measure=meas)
            # i think i mean to use either d or u below as offset is left or right of the line
            if reverse is True:
                d = geom.length - pp['d']
            else: d = pp['d']
            if d > 0 and d < geom.length:
                rows.append([d, pp['pt'].x, pp['pt'].y, pp['pt'].z, pp['o'], edge])
    rows_df = pnd.DataFrame(rows, columns=['s', 'x', 'y', 'z', 'd', 'edge'])
    return rows_df

def rebase_addresses(point_addresses, edge_addresses):
    """Calculate point distances from a node.

    The DataFrame columns are:

        :ds (float): cost path distance from the projected point the outlet node
        :s (float): distance along the edge geometry
        :x (float): projected point x coordinate
        :y (float): projected point y coordinate
        :z (float): projected point z coordinate
        :d (float): offset distance, or distance from the point to its projection
        :edge (tuple): tuple of node identifiers identifying an edge
        :address_v (float): cost path distance from the edge end node to the outlet node

    Parameters:
        point_addresses (DataFrame): point address information
        edge_addresses (DataFrame): edge address information

    Returns:
        result (DataFrame): point address information relative to an outlet node in a network

    """
    result = pnd.merge(point_addresses, edge_addresses, on='edge')
    result['ds'] = result['s'] + result['address_v']
    return result
