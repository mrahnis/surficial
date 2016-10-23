import networkx as nx
from networkx import DiGraph
import pandas as pnd
from shapely.geometry import Point, MultiLineString
from surficial.ops.shape import measure

class Alignment(DiGraph):
    """A directed network graph of LineStrings.

    Alignment is a subclass of networkx.DiGraph and adds methods for addressing points within
    the network. It represents the set of geometries onto which points of interest are
    projected.

    """
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
            node_from = None
            node_to = None
            for n, data in self.nodes(data=True):
                p = data['geom']
                if p.almost_equals(Point(line.coords[0]), decimal=2):
                    node_from = n
                elif p.almost_equals(Point(line.coords[-1]), decimal=2):
                    node_to = n
            self.add_edge(node_from, node_to, geom=line, len=line.length, meas=measure(line))

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

        The DataFrame columns are:
            edge (tuple): tuple of node identifiers identifying an edge
            address_v (float): the cost path distance between outlet node and edge end node

        Parameters:
            outlet (int): network outlet node ID

        Other Parameters:
            weight (string): name of property to use for weight calculation

        Returns:
            result (DataFrame): edge address information relative to outlet

        """
        addresses = []
        for u, v, _ in self.edges(data=True):
            pathv = self.path_edges(v, outlet)
            distv = self.path_weight(pathv, weight)
            addresses.append([(u, v), distv])
        result = pnd.DataFrame(addresses, columns=['edge', 'address_v'])
        return result

    def edge_buffer(self, distance, edges=None):
        """Return a buffer Polygon around a set of graph edges.

        Parameters:
            distance (float): buffer radius

        Other Parameters:
            edges (list of tuples): optional list of edges to buffer

        Returns:
            polygon (MultiLineString): polygon representing the buffered geometries

        """
        if edges is None:
            edges = self.edges()
        geoms = [self[u][v]['geom'] for (u, v) in edges]
        polygon = MultiLineString(geoms).buffer(distance)
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
        for (u, v) in edges:
            total += self[u][v][weight]
        return total

    def station(self, step, keep_vertices=False):
        """Get a dataframe of regularly spaced stations along graph edges with zero at the start of each graph edge.

        \b
        To improve it needs to regularly space them throughout the network starting from the outlet by tracking the remainder at each edge.

        Parameters:
            step (float): distance spacing between stations

        Other Parameters:
            keep-vertices (boolean): keep the original vertices, or return only the stations

        Returns:
            stations (DataFrame): point information

        """
        from operator import itemgetter

        stations = pnd.DataFrame()
        for u, v, data in self.edges(data=True):
            # get the distance from the downstream node to the
            path = self.path_edges(u, self.outlet())
            path_len = self.path_weight(path, 'len')
            line = data['geom']

            ''' maybe change while statement to for statement below for clarity'''
            # calculate the stations
            stations_tmp = []
            d = 0
            while d < line.length:
                s = path_len - d
                p = line.interpolate(d)
                if p.has_z:
                    stations_tmp.append([s, p.x, p.y, p.z, (u, v)])
                else:
                    stations_tmp.append([s, p.x, p.y, None, (u, v)])
                d += step
            # get the vertices
            if keep_vertices:
                for p in list(line.coords):
                    d = line.project(Point(p))
                    s = path_len - d
                    if len(p) == 3:
                        stations_tmp.append([s, p[0], p[1], p[2], (u, v)])
                    else:
                        stations_tmp.append([s, p[0], p[1], None, (u, v)])
                stations_tmp = sorted(stations_tmp, key=itemgetter(0), reverse=True)
            if stations.empty:
                stations = pnd.DataFrame(stations_tmp, columns=['s', 'x', 'y', 'z', 'edge'])
            else:
                stations = pnd.concat([
                    stations,
                    pnd.DataFrame(stations_tmp, columns=['s', 'x', 'y', 'z', 'edge'])
                    ], ignore_index=True)
        return stations

    def intermediate_nodes(self):
        """Return the set of nodes intermediate between leaf and root nodes.

        Returns:
            node_list (list of int): list of all intermediate node ID values

        """
        node_list = [node for node in self.nodes() if self.out_degree(node) > 0 and self.in_degree(node) > 0]
        return node_list
