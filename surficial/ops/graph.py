import networkx as nx
from shapely.geometry import Point, MultiLineString
import pandas as pnd

from surficial.ops.shape import measure, filter_contains, project2d

def points_to_edge_addresses(graph, points, radius=100, edges=None, reverse=False):
    """Locate points by address along the nearest graph edge.

    Returns a DataFrame describing the addresses (projections) of points, within some distance, onto a set of graph edges.
    The DataFrame columns are:

        :m (float): distance along the edge geometry
        :x (float): projected point x coordinate
        :y (float): projected point y coordinate
        :z (float): projected point z coordinate
        :d (float): offset distance, or distance from the point to its projection
        :edge (tuple): tuple of node identifiers identifying an edge 

    Parameters:
        graph (DiGraph): directed network graph
        points (list of Points): points to project

    Other Parameters:
        radius (float): buffer radius
        edges (list of tuples): edge tuples onto which points will be projected, if None then all edges in graph are used
        reverse (bool): reverse vertex ordering

    Returns:
        rows_df (DataFrame): point address information relative to individual edges

    """
    if edges is None:
        edges = graph.edges()
        
    rows = []
    for edge in edges:
        buffer = graph.edge_buffer(radius, edges=[edge])
        pts = filter_contains(points, buffer)
        geom = graph[edge[0]][edge[1]]['geom']
        meas = graph[edge[0]][edge[1]]['meas']
        for p in pts:
            pp = project2d(p, geom, measure=meas)
            # i think i mean to use either d or u below as offset is left or right of the line
            if reverse is True:
                m = geom.length - pp['m']
            else: m = pp['m']
            if m > 0 and m < geom.length:
                rows.append([m, pp['pt'].x, pp['pt'].y, pp['pt'].z, pp['d'], edge])
    rows_df = pnd.DataFrame(rows, columns=['m', 'x', 'y', 'z', 'd', 'edge'])
    return rows_df

def rebase_addresses(point_addresses, edge_addresses):
    """Calculate point distances from a node.

    The DataFrame columns are:

        :route_m (float): distance along the route from the projected point the outlet node
        :m (float): distance along the edge geometry
        :x (float): projected point x coordinate
        :y (float): projected point y coordinate
        :z (float): projected point z coordinate
        :d (float): offset distance, or distance from the point to its projection
        :edge (tuple): tuple of node identifiers identifying an edge
        :to_node_address (float): cost path distance from the edge end node to the outlet node

    Parameters:
        point_addresses (DataFrame): point address information
        edge_addresses (DataFrame): edge address information

    Returns:
        result (DataFrame): point address information relative to an outlet node in a network

    """
    result = pnd.merge(point_addresses, edge_addresses, on='edge')
    result['route_m'] = result['m'] + result['to_node_address']
    return result

def remove_spikes(vertices):
    """
    Remove spikes in a series of vertices by calculating an expanding minimum from upstream to downstream
    """
    #zmin = vertices.groupby(pnd.Grouper(key='edge')).expanding().min()['z'].reset_index(drop=True)
    grouped = vertices.groupby('edge')
    zmin = grouped['z'].apply(lambda x: x.expanding().min())
    zmin.name = 'zmin'

    result = pnd.concat([vertices, zmin], axis=1)

    return result
