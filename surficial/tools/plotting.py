from matplotlib.collections import LineCollection

def vertices_to_linecollection(vertices, xcol='x', ycol='y', style=None):
    verts = [list(zip(edge[xcol], edge[ycol])) for _, edge in vertices.groupby('edge')]
    if style != None:
    	lines = LineCollection(verts, **style)
    else:
	    lines = LineCollection(verts)
	    
    return lines