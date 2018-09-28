from matplotlib.collections import LineCollection


def df_extents(df, xcol='x', ycol='y'):
    from collections import namedtuple

    Extents = namedtuple('Extents', ['minx', 'miny', 'maxx', 'maxy'])

    extents = Extents(df[xcol].min(), df[ycol].min(), df[xcol].max(), df[ycol].max())
    return extents


def cols_to_linecollection(df, xcol='x', ycol='y', style=None):
    """Return a matplotlib LineCollection given two pandas DataFrame columns

    Parameters:
        df (DataFrame): DataFrame containing xy data

    Other Parameters:
        x (string): x column name
        y (string): y column name

    Returns:
        collection (LineCollection): matplotlib LineCollection

    """
    verts = [list(zip(edge[xcol], edge[ycol])) for _, edge in df.groupby('edge')]
    if style != None:
        collection = LineCollection(verts, **style)
    else:
        collection = LineCollection(verts)

    return collection
