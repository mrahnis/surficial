import pandas as pnd

from surficial.ops.graph import extend_edge

def remove_spikes(graph, start=None, goal=None, column='z'):
    """Remove spikes from a graph or a subset of edges using an expanding minimum

    Parameters:
        graph (Alignment): directed network graph

    Other Parameters:
        start (int): starting/from node
        goal (int): goal/to node
        column (string): column from which to remove spikes

    Returns:
        result (DataFrame): graph vertices with new despiked column 'zmin' 

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

def remove_spikes_edgewise(vertices):
    """Remove spikes by calculating an expanding minimum from upstream to downstream

    Adds a DataFrame column, zmin, to hold the despiked z-values.

    Parameters:
        vertices (DataFrame): vertex coordinates

    Returns:
        result (DataFrame): vertex coordinates with min column

    """
    grouped = vertices.groupby('edge')
    zmin = grouped['z'].apply(lambda x: x.expanding().min())
    zmin.name = 'zmin'

    result = pnd.concat([vertices, zmin], axis=1)

    return result

def rolling_mean_edgewise(points):
    """Calculate a rolling mean on a series of point z values

    Parameters:
        points (DataFrame): coordinate addresses

    Returns:
        result (DataFrame): coordinate addresses with mean column 
    """
    grouped = points.groupby('edge')
    means = grouped['z'].apply(lambda x: x.rolling(window=9, win_type='triang', center=True).mean())
    means.name = 'zmean'

    result = pnd.concat([points, means], axis=1)
 
    return result
 
def difference(series1, series2, column1='zmean', column2='zmin'):
    """Calculate the difference between zmin and zmean

    Parameters:
        series1 (DataFrame): first series
        series2 (DataFrame): second series
        column1 (string): first series column
        column2 (string): second series column

    """
    combined = pnd.concat([series1, series2], axis=0, ignore_index=True)
    grouped = combined.groupby('edge')
    for edge, group in grouped:
        aligned = group.sort_values(by='m')
        aligned_m = aligned.set_index('m')
        filled_series = aligned_m.interpolate(method='values')
        filled_series['diff'] = filled_series[column1] - filled_series[column2]

def roll_down(graph, start, goal, window):
    """Perform an operation on a list of path edges

    Parameters:
        graph (Alignment): directed network graph
        start (int): start/from node
        goal (int): goal/to node
        window (int): window width in number of vertices

    """
    vertices = graph.vertices
    edges = list(graph.path_edges(start, goal))
    for i, edge in enumerate(edges):
        pre_window = pnd.DataFrame()
        post_window = pnd.DataFrame()

        verts = vertices[vertices['edge']==edge]
        if i > 0:
            pre_edge = get_neighbor_edge(graph, edge[0], direction='up', column='z', statistic='min')
            pre_window = vertices[vertices['edge']==pre_edge].tail(window) 
        if i <= len(edges)-2:
            post_window = vertices[vertices['edge']==edges[i+1]].head(window)

        if pre_window.empty != True and post_window.empty != True:
            extended = pnd.concat([pre_window, verts, post_window])
        elif pre_window.empty != True:
            extended = pnd.concat([pre_window, verts])
        else:
            extended = pnd.concat([verts, post_window])
        roll = extended.sort_values(by='m_relative')

        roll['roll'] = roll['z'].rolling(window=window, win_type='triang', center=True).mean()

        result = roll[roll['edge']==edge]
        print(result)

def identify_dams(graph, min_grade=1.0, min_drop=1.0, column='zmin'):
    """Identify candidate dam locations

    Iterates over a series of vertices and initiates a cumulative accounting of drop in elevation
    for series of line segments having grade greater than a minimum value. Runs of segments
    having a drop greater than the minimum drop value are identified as candidate dams.

    Fundamental problems in making operations on the graph smooth here:
    Sometimes I want the graph, sometimes I want the vertices, maybe extended to adjacent edge

    Parameters:
        graph (Alignment)

    Other Parameters:
        column (string)
        min_grade (float)
        min_drop (float)

    """

    """
    _, last_vertex = next(edge_data.itertuples())  # take first item from row_iterator
    for i, vertex in edge_iterator:
        rise = vertex['z'] - last_vertex['z']
        run = vertex['m'] - last_vertex['m']
        slope = rise / run
        print(slope)
    """
    result = pnd.DataFrame()
    for edge in graph.edges():
        edge_data = extend_edge(graph, edge, window=10)
        edge_data['rise'] = edge_data['z'] - edge_data['z'].shift(-1)
        edge_data['slope'] = edge_data['rise'] / (edge_data['m'] - edge_data['m'].shift(-1))
        clip = edge_data[edge_data['edge']==edge]
        result = result.append(clip)

    #print(result.head(20))
    return result
