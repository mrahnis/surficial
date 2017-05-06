from operator import itemgetter

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
        edge_rows = []
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
                edge_rows.append([m, pp['pt'].x, pp['pt'].y, pp['pt'].z, pp['d'], edge])
        rows.extend(sorted(edge_rows, key=itemgetter(0), reverse=False))
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
    addresses = pnd.merge(point_addresses, edge_addresses, on='edge')
    addresses['route_m'] = addresses['from_node_address'] - addresses['m']  # + addresses['to_node_address']

    return addresses

def remove_spikes(vertices):
    """Remove spikes by calculating an expanding minimum from upstream to downstream

    Adds a DataFrame column, zmin, to hold the despiked z-values.

    Parameters:
        vertices (DataFrame): vertex coordinates

    Returns:
        result (DataFrame): vertex coordinates

    """
    grouped = vertices.groupby('edge')
    zmin = grouped['z'].apply(lambda x: x.expanding().min())
    zmin.name = 'zmin'

    result = pnd.concat([vertices, zmin], axis=1)

    return result

def rolling_mean(points):
    """Calculate a rolling mean on a series of point z values

    Parameters:
        points (DataFrame)

    Returns:
        result (DataFrame)
    """
    grouped = points.groupby('edge')
    means = grouped['z'].apply(lambda x: x.rolling(window=9, win_type='triang', center=True).mean())
    means.name = 'zmean'

    result = pnd.concat([points, means], axis=1)
 
    return result
 
def difference(series1, series2):
    """Calculate the difference between zmin and zmean

    Parameters:
        series1 (DataFrame)
        series2 (DataFrame)

    """
    combined = pnd.concat([series1, series2], axis=0, ignore_index=True)
    grouped = combined.groupby('edge')
    for edge, group in grouped:
        aligned = group.sort_values(by='m')
        aligned_m = aligned.set_index('m')
        filled_series = aligned_m.interpolate(method='values')
        filled_series['diff'] = filled_series['zmean'] - filled_series['zmin']

def roll_down(graph, start, goal, window):
    """Perform an operation on a list of path edges

    Parameters:
        graph (Alignment)
        start (int)
        goal (int)
        window (int)

    """
    vertices = graph.vertices()
    edges = list(graph.path_edges(start, goal))
    for i, edge in enumerate(edges):
        pre_window = pnd.DataFrame()
        post_window = pnd.DataFrame()

        verts = vertices[vertices['edge']==edge]
        if i > 0:
            #pre_window = vertices[vertices['edge']==edges[i-1]].tail(window)
            pre_window = get_pre_window(graph.in_edges(edge[0]), vertices, window, 'z')
        if i <= len(edges)-2:
            post_window = vertices[vertices['edge']==edges[i+1]].head(window)

        if pre_window.empty != True and post_window.empty != True:
            extended = pnd.concat([pre_window, verts, post_window])
        elif pre_window.empty != True:
            extended = pnd.concat([pre_window, verts])
        else:
            extended = pnd.concat([verts, post_window])
        roll = extended.sort_values(by='route_m')

        roll['roll'] = roll['z'].rolling(window=window, win_type='triang', center=True).mean()

        result = roll[roll['edge']==edge]
        print(result)

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
        tmp = vertices[vertices['edge']==edge].tail(window)
        if val:
            if tmp[column].min() < val:
                in_window = tmp
        else:
            in_window = tmp
            val = tmp[column].min()
    return in_window


def get_min_neighbor_edge(graph, edge, column='z', direction='up', window=None):
    """Return the neighboring edge having the lowest minimum value

    Parameters:
        graph (Alignment)
        edge (tuple)

    Other Parameters:
        column (string)
        direction (string)
        window (int)

    Returns:
        result (tuple): edge having the lowest minimum value

    """
    vertices = graph.vertices()
    min_edge = None
    min_val = None

    if direction=='up':
        edges = [(i, edge[0]) for i in graph.predecessors(edge[0])]
    else:
        edges = [(edge[1], i) for i in graph.successors(edge[1])]

    if len(edges) > 0:
        for test_edge in edges:
            if window:
                test_df = vertices[vertices['edge']==test_edge].tail(window)
            else:
                test_df = vertices[vertices['edge']==test_edge]
            test_val = test_df[column].min()
            if min_val:
                if test_val < min_val:
                    min_edge = test_edge
                    min_val = test_val
            else:
                min_edge = test_edge
                min_val = test_val

    return min_edge

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
    vertices = graph.vertices()
    edge_vertices = vertices[vertices['edge']==edge]

    if statistic == 'min':
        pre_edge = get_min_neighbor_edge(graph, edge, column='z', direction='up', window=window)
        post_edge = get_min_neighbor_edge(graph, edge, column='z', direction='down', window=window)

    pre_window = pnd.DataFrame()
    post_window = pnd.DataFrame()
    if pre_edge:
        pre_window = vertices[vertices['edge']==pre_edge].tail(window)
    if post_edge:
        post_window = vertices[vertices['edge']==post_edge].head(window)
    result = pnd.concat([pre_window, edge_vertices, post_window])

    return result

def remove_spikes_graph(graph, start=None, goal=None, column='z'):
    """Remove spikes from a graph or a subset of edges using an expanding minimum

    Parameters:
        graph (Alignment):

    Other Parameters:
        start (int):
        goal (int):
        column (string):

    """
    if start and goal:
        edges = graph.path_edges(start, goal)
    elif start and not goal:
        edges = graph.path_edges(start, graph.outlet())
    elif goal and not start:
        subgraph = graph.subgraph(nx.ancestors(graph, goal))
        edges = subgraph.edges()
    else:
        edges = graph.edges()

    result = pnd.DataFrame()
    for edge in edges:
        edge_data = extend_edge(graph, edge, window=40)
        edge_data['zmin'] = edge_data[column].expanding().min()
        clip = edge_data[edge_data['edge']==edge]
        result = result.append(clip)

    return result

def edge_address_to_point(graph, edge, m):
    """Return a Point location given an edge address within an Alignment

    Parameters:
        graph (Alignment)
        edge (tuple): tuple identifying the edge
        m (float): distance measure along the edge geometry

    Returns:
        point (Point): address location

    """
    line = graph[edge[0]][edge[1]]['geom']
    point = line.interpolate(m)
    
    return point

def identify_dams(graph, min_grade=1.0, min_drop=1.0, column='zmin'):
    """Identify candidate dam locations

    Iterates over a series of vertices and initiates a cumulative accounting of drop in elevation
    for series of line segments having grade greater than a minimum value. Runs of segments
    having a drop greater than the minimum drop value are identified as candidate dams.

    Parameters:
        graph (Alignment)

    Other Parameters:
        column (string)
        min_grade (float)
        min_drop (float)

    """

    # need to move vertices() into init so i can stop doing alignment.vertices()
    # may want to store calculations in separate dataframes from vertices
    vertices = graph.vertices()
    vertices = surficial.remove_spikes_graph(graph)

    indices = []
    for edge in graph.edges():
        edge_data = extend_edge(graph, edge, window=10)
        idx = None
        drop = 0.0
        #edge_data['rise'] = edge_data['zmin'] - edge_data['zmin'].shift(-1)
        #edge_data['slope'] = edge_data['rise'] / (edge_data['m'] - edge_data['m'].shift(-1))
        #print(edge_data['rise'])
        #print(edge_data['slope'])
        print(edge_data)
        """
        _, last_vertex = next(edge_data.itertuples())  # take first item from row_iterator
        for i, vertex in edge_iterator:
            rise = vertex['z'] - last_vertex['z']
            run = vertex['m'] - last_vertex['m']
            slope = rise / run
            print(slope)
        """
