from operator import itemgetter

import networkx as nx
from shapely.geometry import Point, MultiLineString
import pandas as pnd

from surficial.ops.shape import measure, filter_contains, project2d


def address_to_point(graph, edge, m):
    """Return a Point location given an edge address within an Alignment

    Parameters:
        graph (Alignment): directed network graph
        edge (tuple): tuple identifying the edge
        m (float): distance measure along the edge geometry

    Returns:
        point (Point): address location

    """
    line = graph[edge[0]][edge[1]]['geom']
    point = line.interpolate(m)

    return point


def points_to_addresses(graph, points, radius=100, edges=None, reverse=False):
    """Locate points by address along the nearest graph edge.

    Returns a DataFrame describing the addresses (projections) of points, within some distance, onto a set of graph edges.

    Parameters:
        graph (DiGraph): directed network graph
        points (list of Points): points to project

    Other Parameters:
        radius (float): buffer radius
        edges (list of tuples): edge tuples onto which points will be projected, if None then all edges in graph are used
        reverse (bool): reverse vertex ordering

    Returns:
        result (DataFrame): DataFrame of point address information relative to individual edges

        :m (float): distance along the edge geometry
        :x (float): projected point x coordinate
        :y (float): projected point y coordinate
        :z (float): projected point z coordinate
        :d (float): offset distance, or distance from the point to its projection
        :edge (tuple): tuple of node identifiers identifying an edge 
    """
    if edges is None:
        edges = graph.edges()

    rows = []
    for edge in edges:
        edge_rows = []
        buffer = graph.edge_buffer(radius, edges=[edge])
        pts = filter_contains(points, buffer)
        geom = graph[edge[0]][edge[1]]['geom']
        meas = graph[edge[0]][edge[1]]['meas']
        for p in pts:
            pp = project2d(p, geom, measure=meas)
            if reverse is True:
                m = geom.length - pp['m']
            else:
                m = pp['m']
            if m > 0 and m < geom.length:
                edge_rows.append([m, pp['pt'].x, pp['pt'].y, pp['pt'].z, pp['d'], edge])
        rows.extend(sorted(edge_rows, key=itemgetter(0), reverse=False))
    result = pnd.DataFrame(rows, columns=['m', 'x', 'y', 'z', 'd', 'edge'])

    return result


def get_path_distances(point_addresses, edge_addresses):
    """Calculate point distances from a node.

    Parameters:
        point_addresses (DataFrame): point address information
        edge_addresses (DataFrame): edge address information

    Returns:
        result (DataFrame): DataFrame of point address information relative to an outlet node in a network

        :m (float): distance along the edge geometry
        :x (float): projected point x coordinate
        :y (float): projected point y coordinate
        :z (float): projected point z coordinate
        :d (float): offset distance, or distance from the point to its projection
        :edge (tuple): tuple of node identifiers identifying an edge
        :from_node_address (float): cost path distance from the edge start node to the outlet node
        :to_node_address (float): cost path distance from the edge end node to the outlet node
        :path_m (float): path distance from the point to the outlet node
    """
    addresses = pnd.merge(point_addresses, edge_addresses, on='edge')
    addresses['path_m'] = addresses['from_node_address'] - addresses['m']

    return addresses


def get_pre_window(edges, vertices, window, column, statistic='min'):
    """Determine a 'winning' edge where a node has multiple edges

    Parameters:
        edges (list of tuples)
        vertices (DataFrame)
        window (int)
        column (string)
        statistic (string)

    """
    in_window = pnd.DataFrame()
    val = None
    for edge in edges:
        tmp = vertices[vertices['edge'] == edge].tail(window)
        if val:
            if tmp[column].min() < val:
                in_window = tmp
        else:
            in_window = tmp
            val = tmp[column].min()
    return in_window


def get_neighbor_edge(graph, edge, column='z', direction='up', window=None, statistic='min'):
    """Return the neighboring edge having the lowest minimum value

    Parameters:
        graph (Alignment): directed network graph
        edge (tuple): edge for which to determine a neighbor

    Other Parameters:
        column (string): column to test in vertices
        direction (string): 'up' tests predecessor edges; 'down' tests successors
        window (int): number of neighbor vertices to test 
        statistic (string): test statistic

    Returns:
        result (tuple): edge meeting the criteria

    """
    vertices = graph.vertices
    result = None
    val = None

    if direction == 'up':
        neighbors = [(i, edge[0]) for i in graph.predecessors(edge[0])]
    else:
        neighbors = [(edge[1], i) for i in graph.successors(edge[1])]

    if len(neighbors) > 0:
        for neighbor in neighbors:
            if window:
                test_verts = vertices[vertices['edge'] == neighbor].tail(window)
            else:
                test_verts = vertices[vertices['edge'] == neighbor]

            if statistic == 'min':
                test_val = test_verts[column].min()
                if val:
                    if test_val < val:
                        result = neighbor
                        val = test_val
                else:
                    result = neighbor
                    val = test_val

    return result


def extend_edge(graph, edge, window=10, statistic="min"):
    """Extend an edge using vertices from neighboring edges

    Parameters:
        graph (Alignment)
        edge (tuple): edge to extend

    Other Parameters:
        window (int): number of vertices to extend the edge
        statistic (string): function used to determine which edge to use among several

    Returns:
        result (DataFrame): vertices of the edge along with vertices from preceeding and successor edges

    """
    vertices = graph.vertices
    edge_vertices = vertices[vertices['edge'] == edge]

    if statistic == 'min':
        pre_edge = get_neighbor_edge(graph, edge, column='z', direction='up', window=window, statistic=statistic)
        post_edge = get_neighbor_edge(graph, edge, column='z', direction='down', window=window, statistic=statistic)

    pre_window = pnd.DataFrame()
    post_window = pnd.DataFrame()
    if pre_edge:
        pre_window = vertices[vertices['edge'] == pre_edge].tail(window)
    if post_edge:
        post_window = vertices[vertices['edge'] == post_edge].head(window)
    result = pnd.concat([pre_window, edge_vertices, post_window])

    return result
