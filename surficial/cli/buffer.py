import sys
import logging

import networkx as nx
import fiona
from shapely.geometry import shape, mapping, Point, LineString
import click

import surficial

@click.command()
@click.argument('stream_f', nargs=1, type=click.Path(exists=True), metavar='<stream_file>')
@click.argument('output_f', nargs=1, type=click.Path(), metavar='<output_file>')
@click.argument('distance', nargs=1, type=click.FLOAT, metavar='<float>')
@click.option('-s', '--source', nargs=1, type=click.INT, metavar='<int>', help="Source node ID")
@click.option('-o', '--outlet', nargs=1, type=click.INT, metavar='<int>', help="Outlet node ID")
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode')
def cli(stream_f, output_f, distance, source, outlet, verbose):
    """
    Buffers a network graph or path within a network graph

    \b
    Example:
    buffer examples/white-clay-cr/stream_ln_nhd_sp.shp buf.shp 100.0 -s 5
    """

    # stream
    with fiona.open(stream_f) as stream_src:
        lines = [shape(line['geometry']) for line in stream_src]
        source_driver = stream_src.driver
        source_crs = stream_src.crs

    # make the graph
    g = surficial.construct(lines)

    if not outlet:
        outlet = surficial.get_outlet(g)
    if not source:
        path = g.edges()
    else:
        path = list(surficial.get_path_edges(g, source, outlet))
    buf = surficial.get_edge_buffer(g, distance, edges=path)

    sink_schema = {
        'geometry': 'Polygon',
        'properties': {'id': 'int'},
    }

    with fiona.open(
    	output_f,
    	'w',
    	driver=source_driver,
    	crs=source_crs,
    	schema=sink_schema) as c:
            c.write({
            	'geometry': mapping(buf),
            	'properties': {'id': 0},
        	})
    print(c.closed)