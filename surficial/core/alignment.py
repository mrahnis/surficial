import warnings
from operator import itemgetter

import networkx as nx
from networkx import DiGraph
import pandas as pnd
from shapely.geometry import Point, MultiLineString

from surficial.ops.shape import measure, linestring_to_vertices, linestring_to_stations, densify_linestring

class Alignment(DiGraph):
    """A directed network graph of LineStrings.

    Alignment is a subclass of networkx.DiGraph and adds methods for addressing points within
    the network. It represents the set of geometries onto which points of interest are
    projected.

    """

    def _vertices(self):
        """Get a dataframe of the vertices

        Returns:
            vertices (DataFrame): DataFrame of point information

            :m (float): distance from the edge endpoint
            :x (float): x coordinate
            :y (float): y coordinate
            :z (float): z coordinate
            :edge (tuple): pair of graph nodes (from, to)
        """
        result = pnd.DataFrame()
        for from_node, to_node, data in self.edges(data=True):
            path = self.path_edges(from_node, self.outlet())
            path_len = self.path_weight(path, 'len')

            line_vertices = pnd.DataFrame(linestring_to_vertices(data['geom']), columns=['m','x','y','z'])
            line_vertices['route_m'] = path_len - line_vertices['m']
            line_vertices['edge'] = [(from_node, to_node) for vertex in range(line_vertices.shape[0])] 

            if result.empty:
                result = line_vertices
            else:
                result = pnd.concat([result, line_vertices], ignore_index=True)

        return result

    def __init__(self, lines):
        """Construct a directed graph from a set of LineStrings.

        Parameters:
            lines (list of LineString): geometries in the network

        Returns:
            graph (DiGraph): directed network graph

        """
        super().__init__()

        # add the nodes
        endpoints = []
        for line in lines:
            endpoints.append(line.coords[0])
            endpoints.append(line.coords[-1])
        for i, p in enumerate(set(endpoints)):
            self.add_node(i, geom=Point(p))

        # add the edges
        for line in lines:
            from_node = None
            to_node = None
            for n, data in self.nodes(data=True):
                p = data['geom']
                if p.equals(Point(line.coords[0])):
                    from_node = n
                elif p.equals(Point(line.coords[-1])):
                    to_node = n
            self.add_edge(from_node, to_node, geom=line, len=line.length, meas=measure(line))

        if nx.isolates(self):
            warnings.warn("Found isolated nodes, check input geometries using the repair subcommand. Exiting now.")
        if len(list(nx.connected_component_subgraphs(self.to_undirected()))) > 1:
            warnings.warn("Found multiple subgraphs, check input geometries using the repair subcommand. Exiting now.")

        self.vertices = self._vertices()

    def outlet(self):
        """Return the root node in a directed graph.

        In a stream network this represents the drainage outlet.

        Returns:
            n (int): outlet node ID

        """
        for node in self.nodes():
            if self.out_degree(node) == 0:
                return node

    def edge_addresses(self, outlet, weight='len'):
        """Calculate cost path distances from a given node to each graph edge end node. 

        Parameters:
            outlet (int): network outlet node ID

        Other Parameters:
            weight (string): name of property to use for weight calculation

        Returns:
            result (DataFrame): DataFrame of edge address information relative to outlet

            :edge (tuple): tuple of node identifiers identifying an edge
            :to_node_address (float): the cost path distance between outlet node and edge end node

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

    def edge_buffer(self, radius, edges=None):
        """Return a buffer Polygon around a set of graph edges.

        \b
        Example:
        path = list(alignment.path_edges(1, outlet))
        buf = PolygonPatch(alignment.edge_buffer(100.0, edges=path), fc=BLUE, ec=BLUE, alpha=0.5, zorder=2)

        Parameters:
            radius (float): buffer radius

        Other Parameters:
            edges (list of tuples): optional list of edges to buffer

        Returns:
            polygon (MultiLineString): polygon representing the buffered geometries

        """
        if edges is None:
            edges = self.edges()
        geoms = [self[from_node][to_node]['geom'] for (from_node, to_node) in edges]
        polygon = MultiLineString(geoms).buffer(radius)
        return polygon

    def path_edges(self, start, goal, weight=None):
        """Return the set of graph edges making up a shortest path.

        Parameters:
            start (int): starting node ID
            goal (int): goal node ID

        Other Parameters:
            weight (string): name of property to use for weight calculation

        Returns:
            edges (list of tuples): list of edges making up the path

        """
        path = nx.shortest_path(self, start, goal, weight=weight)
        edges = zip(path[:-1], path[1:])

        return edges

    def path_weight(self, edges, weight):
        """Return the path weight of a set of graph edges.

        Parameters:
            edges (list of tuples): list of edges making up the path
            weight (string): name of property to use for weight calculation

        Returns:
            total (float): path weight

        """
        total = 0
        for (from_node, to_node) in edges:
            total += self[from_node][to_node][weight]
        return total

    def station(self, step):
        """Get a dataframe of regularly spaced stations along graph edges.

        Parameters:
            step (float): distance spacing between stations

        Returns:
            stations (DataFrame): DataFrame containing point information

            :m (float): path distance from the to_node endpoint
            :x (float): x coordinate
            :y (float): y coordinate
            :z (float): z coordinate
            :edge (tuple): pair of graph nodes (from, to)
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
            line_stations['route_m'] = path_len - line_stations['m']
            line_stations['edge'] = [(from_node, to_node) for station in range(line_stations.shape[0])] 

            if stations.empty:
                stations = line_stations
            else:
                stations = pnd.concat([stations, line_stations], ignore_index=True)

        return stations

    def intermediate_nodes(self):
        """Return the set of nodes intermediate between leaf and root nodes.

        Returns:
            node_list (list of int): list of all intermediate node ID values

        """
        node_list = [node for node in self.nodes() if self.out_degree(node) > 0 and self.in_degree(node) > 0]
        return node_list
