import networkx as nx
from shapely.geometry import Point, MultiLineString
import pandas as pnd

from surficial.ops.shape import measure_verts, filter_points, project_point_onto_line

def construct(lines):
    """Construct a directed graph from a set of LineStrings.

    Parameters:
        lines (list of LineString): geometries in the network

    Returns:
        graph (DiGraph): directed network graph

    """
    graph = nx.DiGraph()

    # add the nodes
    endpoints = []
    for line in lines:
        endpoints.append(line.coords[0])
        endpoints.append(line.coords[-1])
    for i, p in enumerate(set(endpoints)):
        graph.add_node(i, geom=Point(p))

    # add the edges
    for line in lines:
        node_from = None
        node_to = None
        for n, data in graph.nodes(data=True):
            p = data['geom']
            if p.almost_equals(Point(line.coords[0]), decimal=2):
                node_from = n
            elif p.almost_equals(Point(line.coords[-1]), decimal=2):
                node_to = n
        graph.add_edge(node_from, node_to, geom=line, len=line.length, meas=measure_verts(line))

    return graph

def get_path_edges(graph, start, goal, weight=None):
    """Return the set of graph edges making up a shortest path.

    Parameters:
        graph (DiGraph): directed network graph
        start (int): starting node ID
        goal (int): goal node ID
        weight (string): name of property to use for weight calculation

    Returns:
        edges (list of tuples): list of edges making up the path

    """
    path = nx.shortest_path(graph, start, goal, weight=weight)
    edges = zip(path[:-1], path[1:])
    return edges

def get_path_weight(graph, edges, weight):
    """Return the path weight of a set of graph edges.

    Parameters:
        graph (DiGraph): directed network graph
        edges (list of tuples): list of edges making up the path
        weight (string): name of property to use for weight calculation

    Returns:
        total (float): path weight

    """
    total = 0
    for (u, v) in edges:
        total += graph[u][v][weight]
    return total

def get_outlet(graph):
    """Return the root node in a directed graph. This represents the drainage outlet.

    Parameters:
        graph (DiGraph): directed network graph

    Returns:
        n (int): outlet node ID

    """
    for node in graph.nodes():
        if graph.out_degree(node) == 0:
            return node

def get_intermediate_nodes(graph):
    """Return the set of nodes intermediate between leaf and root nodes.

    Parameters:
        graph (DiGraph): directed network graph

    Returns:
        n (list of int): list of all intermediate node ID values

    """
    node_list = [node for node in graph.nodes() if graph.out_degree(node) > 0 and graph.in_degree(node) > 0]
    return node_list

def get_edge_buffer(graph, distance, edges=None):
    """Return a buffer Polygon around a set of graph edges.

    Parameters:
        graph (DiGraph): directed network graph
        distance (float): buffer radius
        edges (list of tuples): optional list of edges to buffer

    Returns:
        polygon (MultiLineString): polygon representing the buffered geometries

    """
    if edges is None:
        edges = graph.edges()
    geoms = [graph[u][v]['geom'] for (u, v) in edges]
    polygon = MultiLineString(geoms).buffer(distance)
    return polygon

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
        buffer = get_edge_buffer(graph, distance, edges=[edge])
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

def address_edges(graph, outlet, weight='len'):
    """Return a DataFrame of addresses for a list of graph edges

    Parameters:
        graph (DiGraph): directed network graph
        outlet (int): network outlet node ID
        weight (string): name of property to use for weight calculation

    Returns:
        result (DataFrame): edge address information relative to outlet

    """
    addresses = []
    for u, v, _ in graph.edges(data=True):
        pathv = get_path_edges(graph, v, outlet)
        distv = get_path_weight(graph, pathv, weight)
        addresses.append([(u, v), distv])
    result = pnd.DataFrame(addresses, columns=['edge', 'address_v'])
    return result

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
