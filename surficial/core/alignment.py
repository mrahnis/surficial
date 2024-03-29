from __future__ import annotations

import sys
import warnings
import inspect
from typing import Union, Optional, Iterable

import networkx as nx
from networkx import DiGraph
import pandas as pnd

from shapely.geometry import Point, LineString, MultiLineString
from shapely.ops import transform, unary_union
from surficial.ops.graph import extend_edge, get_neighbor_edge
from surficial.ops.shape import measure, linestring_to_vertices, linestring_to_stations

ISOLATED_NODES = "Found isolated nodes. Use the repair subcommand to check. Exiting now."
MULTIPLE_SUBGRAPHS = "Found multiple subgraphs. Use the repair subcommand to check. Exiting now."


class Alignment(DiGraph):
    """A directed network graph of LineStrings

    Alignment is a subclass of networkx.DiGraph and adds methods for addressing
    points within the network. It represents the set of geometries onto which
    points of interest are projected.

    """

    def add_geometries(self, lines: list[tuple[str, LineString]]):
        """Construct a directed graph from a set of LineStrings

        Parameters:
            lines: geometries in the network

        Returns:
            directed network graph

        """
        # add the nodes
        endpoints = []
        for _, line in lines:
            endpoints.append(line.coords[0])
            endpoints.append(line.coords[-1])
        for i, p in enumerate(set(endpoints)):
            self.add_node(i, geom=Point(p))

        # add the edges
        for _, line in lines:
            from_node = None
            to_node = None
            for n, data in self.nodes(data=True):
                p = data['geom']
                if p.equals(Point(line.coords[0])):
                    from_node = n
                elif p.equals(Point(line.coords[-1])):
                    to_node = n
            self.add_edge(from_node, to_node, geom=line, len=line.length, meas=measure(line))

        if nx.number_of_isolates(self) > 1:
            warnings.warn(ISOLATED_NODES)
    
        if nx.number_connected_components(self.to_undirected()) > 1:
            print([len(c) for c in sorted(nx.connected_components(self.to_undirected()), key=len, reverse=True)])
            warnings.warn(MULTIPLE_SUBGRAPHS)
            # sys.exit()

        # things fail with multiple connected component subgraphs
        # get_vertices will fail because...
        # path_edges() calculates distance to an assumed single outlet for all vertices


    def get_vertices(self):
        """Get a dataframe of the vertices

        Returns:
            vertices (pandas.DataFrame): point information

            ======  ====================================================
            m       distance from the edge start endpoint (as `float`)
            x       x coordinate (as `float`)
            y       y coordinate (as `float`)
            z       z coordinate (as `float`)
            edge    pair of graph nodes: from, to (as `tuple[int, int]`)
            path_m  distance from the edge end endpoint (as `float`)
            ======  ====================================================
        """

        # make sure we're not calling this repeatedly
        # curframe = inspect.currentframe()
        # calframe = inspect.getouterframes(curframe, 2)
        # print('caller name:', calframe[1][3])

        result = pnd.DataFrame()
        for from_node, to_node, data in self.edges(data=True):
            path = self.path_edges(from_node, self.outlet())
            path_len = self.path_weight(path, 'len')

            line_vertices = pnd.DataFrame(linestring_to_vertices(data['geom']),
                                          columns=['m', 'x', 'y', 'z'])
            line_vertices['edge'] = [(from_node, to_node)] * len(line_vertices)
            line_vertices['path_m'] = path_len - line_vertices['m']

            if result.empty:
                result = line_vertices
            else:
                result = pnd.concat([result, line_vertices], ignore_index=True)

        return result


    def outlet(self) -> int:
        """Return the root node in a directed graph

        In a stream network this represents the drainage outlet.

        Returns:
            outlet node ID

        """
        for node in self.nodes():
            if self.out_degree(node) == 0:
                return node

    def edge_addresses(self, outlet: int, weight: str = 'len') -> pnd.DataFrame:
        """Calculate cost path distances from a given node to each graph edge end node

        Parameters:
            outlet: network outlet node ID

        Other Parameters:
            weight: name of property to use for weight calculation

        Returns:
            pandas.DataFrame of edge address information relative to outlet

            =================  =======================================================================
            edge               tuple of node identifiers identifying an edge (as `tuple[int, int]`)
            from_node_address  cost path distance between outlet node and edge start node (as `float`)
            to_node_address    cost path distance between outlet node and edge end node (as `float`)
            =================  =======================================================================
        """
        addresses = []
        for from_node, to_node, _ in self.edges(data=True):
            to_node_path = self.path_edges(to_node, outlet)
            to_node_dist = self.path_weight(to_node_path, weight)

            from_node_path = self.path_edges(from_node, outlet)
            from_node_dist = self.path_weight(from_node_path, weight)

            addresses.append([(from_node, to_node), from_node_dist, to_node_dist])
        result = pnd.DataFrame(addresses, columns=['edge', 'from_node_address', 'to_node_address'])

        return result

    def edge_buffer(
        self,
        radius: Union[int, float] = 1.0,
        edges: Optional[Iterable[tuple[int, int]]] = None
    ) -> MultiLineString:
        """Return a buffer Polygon around a set of graph edges

        Example:
            path = list(alignment.path_edges(1, outlet))
            buf = PolygonPatch(alignment.edge_buffer(100.0, edges=path), fc=BLUE, ec=BLUE, alpha=0.5, zorder=2)

        Parameters:
            radius: buffer radius

        Other Parameters:
            edges: optional list of edges to buffer

        Returns:
            polygon representing the buffered geometries

        """
        if edges is None:
            edges = self.edges()
        geoms = [self[from_node][to_node]['geom'] for (from_node, to_node) in edges]
        polygon = MultiLineString(geoms).buffer(radius)

        # bufs = [geom.buffer(radius) for geom in new_geoms]
        # polygon = unary_union(bufs)

        return polygon

    def path_edges(
        self,
        start: int,
        goal: int,
        weight: Optional[str] = None
    ) -> Iterable[tuple[int, int]]:
        """Return the set of graph edges making up a shortest path

        Parameters:
            start: starting node ID
            goal: goal node ID

        Other Parameters:
            weight: name of property to use for weight calculation

        Returns:
            edges making up the path

        """
        path = nx.shortest_path(self, start, goal, weight=weight)
        edges = zip(path[:-1], path[1:])

        return edges

    def path_weight(self, edges: Iterable[tuple[int, int]], weight: str) -> float:
        """Return the path weight of a set of graph edges

        Parameters:
            edges: list of edges making up the path
            weight: name of property to use for weight calculation

        Returns:
            total path weight

        """
        total = 0
        for (from_node, to_node) in edges:
            total += self[from_node][to_node][weight]
        return total

    def station(self, step: float) -> pnd.DataFrame:
        """Get a dataframe of regularly spaced stations along graph edges

        Parameters:
            step: distance spacing between stations

        Returns:
            pandas.DataFrame containing station point information

            ======  ====================================================
            m       path distance from the to_node endpoint (as `float`)
            x       x coordinate (as `float`)
            y       y coordinate (as `float`)
            z       z coordinate (as `float`)
            edge    pair of graph nodes: from, to (as `tuple[int, int]`)
            path_m  path distance from the outlet (as `float`)
            ======  ====================================================
        """
        edge_addresses = self.edge_addresses(self.outlet())
        stations = pnd.DataFrame()
        for from_node, to_node, data in self.edges(data=True):
            path = self.path_edges(from_node, self.outlet())
            path_len = self.path_weight(path, 'len')
            line = data['geom']

            end_address = edge_addresses[edge_addresses['edge'] == (from_node, to_node)]
            start = (end_address.iloc[0]['to_node_address'] + line.length) % step

            line_stations = pnd.DataFrame(linestring_to_stations(line, position=start, step=step), columns=['m', 'x', 'y', 'z'])
            line_stations['edge'] = [(from_node, to_node) for _ in range(line_stations.shape[0])]
            line_stations['path_m'] = path_len - line_stations['m']

            if stations.empty:
                stations = line_stations
            else:
                stations = pnd.concat([stations, line_stations], ignore_index=True)

        return stations

    def intermediate_nodes(self) -> list[int]:
        """Return the set of nodes intermediate between leaf and root nodes

        Returns:
            list of all intermediate node ID values

        """
        node_list = [node for node in self.nodes()
                     if self.out_degree(node) > 0 and self.in_degree(node) > 0]
        return node_list


def remove_spikes(
    graph: Alignment,
    start: Union[None, int] = None,
    goal: Union[None, int] = None,
    column: str = 'z',
    vertices: Union[pnd.DataFrame, None] = None
) -> pnd.DataFrame:
    """Remove spikes from a graph or a subset of edges using an expanding minimum

    Parameters:
        graph: directed network graph

    Other Parameters:
        start: starting/from node
        goal: goal/to node
        column: column from which to remove spikes

    Returns:
        pandas.DataFrame of graph vertices with new despiked column 'zmin'

        ======  ====================================================
        m       path distance from the to_node endpoint (as `float`)
        x       x coordinate (as `float`)
        y       y coordinate (as `float`)
        z       z coordinate (as `float`)
        edge    pair of graph nodes: from, to (as `tuple[int, int]`)
        path_m  path distance from the outlet (as `float`)
        zmin    rolling minimum z coordinate (as `float`)
        ======  ====================================================
    """
    if vertices is None:
        vertices = graph.get_vertices()

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
        edge_data = extend_edge(graph, edge, vertices=vertices, window=40)
        edge_data['zmin'] = edge_data[column].expanding().min()
        clip = edge_data[edge_data['edge'] == edge]

        result = pnd.concat([result, clip])

    return result


def roll_down(
    graph: Alignment,
    start: int,
    goal: int,
    window: int,
    vertices: Union[pnd.DataFrame, None] = None
) -> None:
    """Perform an operation on a list of path edges

    Parameters:
        graph: directed network graph
        start: start/from node
        goal: goal/to node
        window: window width in number of vertices

    """
    if vertices is None:
        vertices = graph.get_vertices()

    edges = list(graph.path_edges(start, goal))
    for i, edge in enumerate(edges):
        pre_window = pnd.DataFrame()
        post_window = pnd.DataFrame()

        verts = vertices[vertices['edge'] == edge]
        if i > 0:
            pre_edge = get_neighbor_edge(graph, edge, direction='up', column='z', statistic='min')
            pre_window = vertices[vertices['edge'] == pre_edge].tail(window)
        if i <= len(edges)-2:
            post_window = vertices[vertices['edge'] == edges[i+1]].head(window)

        if pre_window.empty is False and post_window.empty is False:
            extended = pnd.concat([pre_window, verts, post_window])
        elif pre_window.empty is False:
            extended = pnd.concat([pre_window, verts])
        else:
            extended = pnd.concat([verts, post_window])
        roll = extended.sort_values(by='path_m')

        roll['roll'] = roll['z'].rolling(window=window, win_type='triang', center=True).mean()

        result = roll[roll['edge'] == edge]

        print(result)


def slope(
    graph: Alignment,
    column: str = 'z',
    vertices: Union[pnd.DataFrame, None] = None
) -> pnd.DataFrame:
    """Returns a DataFrame with columns for rise and slope between vertices

    Parameters:
        graph: an Alignment

    Other Parameters:
        column: name of column containing the values

    Returns:
        pandas.Dataframe with columns for rise and slope

        ======  ====================================================
        m       path distance from the to_node endpoint (as `float`)
        x       x coordinate (as `float`)
        y       y coordinate (as `float`)
        z       z coordinate (as `float`)
        edge    pair of graph nodes: from, to (as `tuple[int, int]`)
        path_m  path distance from the outlet (as `float`)
        rise    change in given column in downstream direction (as `float`)
        slope   rise over run in the downstream direction (as `float`)
        ======  ====================================================
    """
    if vertices is None:
        vertices = graph.get_vertices()

    result = pnd.DataFrame()
    for edge in graph.edges():
        edge_data = extend_edge(graph, edge, vertices=vertices, window=10)
        # here, rise and slope are treated in the mathematical sense and will be negative for a stream
        edge_data['rise'] = edge_data[column] - edge_data[column].shift(-1)
        edge_data['slope'] = edge_data['rise'] / (edge_data['path_m'].shift(-1) - edge_data['path_m'])
        clip = edge_data[edge_data['edge'] == edge]

        result = pnd.concat([result, clip])

    return result
