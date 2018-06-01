from matplotlib.collections import LineCollection


def vertices_to_linecollection(vertices, xcol='x', ycol='y', style=None):
    """Return a matplotlib LineCollection given two pandas DataFrame columns

    Parameters:
        vertices (DataFrame): DataFrame containing xy data

    Other Parameters:
        x (string): x column name
        y (string): y column name

    Returns:
        collection (LineCollection): matplotlib LineCollection

    """
    verts = [list(zip(edge[xcol], edge[ycol])) for _, edge in vertices.groupby('edge')]
    if style != None:
        collection = LineCollection(verts, **style)
    else:
        collection = LineCollection(verts)

    return collection
