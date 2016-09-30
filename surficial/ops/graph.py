import networkx as nx
from shapely.geometry import Point, MultiLineString
import pandas as pnd

from surficial.ops.shape import measure_verts, filter_points, project_point_onto_line

def construct(lines):
    """
    Construct a directed graph from a set of LineStrings.

    Parameters
    ----------
    lines (array of LineString)

    Returns
    -------
    g (DiGraph)

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
            if p.equals(Point(line.coords[0])):
                node_from = n
            elif p.equals(Point(line.coords[-1])):
                node_to = n
        graph.add_edge(node_from, node_to, geom=line, len=line.length, meas=measure_verts(line))

    return graph

def get_path_edges(graph, start, goal, weight=None):
    """
    Return the set of graph edges making up a shortest path.

    Parameters
    ----------
    graph (DiGraph)
    start (int)
    goal (int)
    weight (string)

    Returns
    -------
    edges (list of tuples)

    """
    path = nx.shortest_path(graph, start, goal, weight=weight)
    edges = zip(path[:-1], path[1:])
    return edges

def get_path_weight(graph, edges, weight):
    """
    Return the path weight of a set of graph edges.

    Parameters
    ----------
    graph (DiGraph)
    edges (list of tuples)
    weight (string)

    Returns
    -------
    total (float)

    """
    total = 0
    for (u, v) in edges:
        total += graph[u][v][weight]
    return total

def get_outlet(graph):
    """
    Return the root node in a directed graph. This represents the drainage outlet.

    Parameters
    ----------
    graph (DiGraph)

    Returns
    -------
    n (int)

    """
    for node in graph.nodes():
        if graph.out_degree(node) == 0:
            return node

def get_intermediate_nodes(graph):
    """
    Return the set of nodes intermediate between leaf and root nodes.

    Parameters
    ----------
    graph (DiGraph)

    Returns
    -------
    n (array of int)

    """
    node_list = [node for node in graph.nodes() if graph.out_degree(node) > 0 and graph.in_degree(node) > 0]
    return node_list

def get_edge_buffer(graph, distance, edges=None):
    """
    Return a buffer Polygon around a set of graph edges.

    Parameters
    ----------
    graph (DiGraph)
    distance (float)
    edges (array of tuples)

    Returns
    -------
    polygon (MultiLineString)

    """
    if edges is None:
        edges = graph.edges()
    geoms = [graph[u][v]['geom'] for (u, v) in edges]
    polygon = MultiLineString(geoms).buffer(distance)
    return polygon

def project_buffer_contents(graph, points, distance, edges=None, reverse=False):
    """
    Return a DataFrame describing the addresses (projections) of points onto a set of graph edges.

    Parameters
    ----------
    graph (DiGraph)
    edges (list of edge tuples)
    points (array of shapely Points)
    distance (float)
    reverse (bool)

    Returns
    -------
    rows_df (DataFrame)

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
    """
    Return a DataFrame of addresses for a list of graph edges

    Parameters
    ----------
    graph (DirectedGraph)
    outlet (int)
    weight (string)

    Returns
    -------
    result (DataFrame)

    """
    addresses = []
    for u, v, _ in graph.edges(data=True):
        pathv = get_path_edges(graph, v, outlet)
        distv = get_path_weight(graph, pathv, weight)
        addresses.append([(u, v), distv])
    result = pnd.DataFrame(addresses, columns=['edge', 'address_v'])
    return result

def address_point_df(point_df, edge_addresses):
    """
    Calculate addresses for a DataFrame of points

    Parameters
    ----------
    point_df (DataFrame)
    edge_addresses (DataFrame)

    Returns
    -------
    result (DataFrame)

    """
    result = pnd.merge(point_df, edge_addresses, on='edge')
    result['ds'] = result['s'] + result['address_v']
    return result
