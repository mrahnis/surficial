import networkx as nx
from shapely.geometry import Point, MultiLineString
import pandas as pnd

from surficial.ops.shape import measure_verts, filter_points, project_point_onto_line

def project_buffer_contents(graph, points, distance, edges=None, reverse=False):
    """Return a DataFrame describing the addresses (projections) of points onto a set of graph edges.

    Parameters:
        graph (DiGraph): directed network graph
        edges (list of tuples): edge tuples onto which points will be projected
        points (list of Points): points to project
        distance (float): buffer radius
        reverse (bool): reverse vertex ordering

    Returns:
        rows_df (DataFrame): point address information relative to individual edges

    """
    if edges is None:
        edges = graph.edges()
        
    rows = []
    for edge in edges:
        buffer = graph.edge_buffer(distance, edges=[edge])
        pts = filter_points(points, buffer)
        geom = graph[edge[0]][edge[1]]['geom']
        meas = graph[edge[0]][edge[1]]['meas']
        for p in pts:
            pp = project_point_onto_line(p, geom, measure=meas)
            # i think i mean to use either d or u below as offset is left or right of the line
            if reverse is True:
                d = geom.length - pp['d']
            else: d = pp['d']
            if d > 0 and d < geom.length:
                rows.append([d, pp['pt'].x, pp['pt'].y, pp['pt'].z, pp['o'], edge])
    rows_df = pnd.DataFrame(rows, columns=['s', 'x', 'y', 'z', 'd', 'edge'])
    return rows_df

def address_point_df(point_df, edge_addresses):
    """Calculate addresses for a DataFrame of points

    Parameters:
        point_df (DataFrame): point address information
        edge_addresses (DataFrame): edge address information

    Returns:
        result (DataFrame): point address information relative to network

    """
    result = pnd.merge(point_df, edge_addresses, on='edge')
    result['ds'] = result['s'] + result['address_v']
    return result
