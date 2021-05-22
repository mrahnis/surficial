from collections import namedtuple
from typing import Union

import pandas as pnd
from matplotlib.collections import LineCollection


Extents = namedtuple('Extents', ['minx', 'miny', 'maxx', 'maxy'])


def df_extents(df: pnd.DataFrame, xcol: str = 'x', ycol: str = 'y') -> Extents:
    """Return 2D coordinate Extents from DataFrame columns

    """
    extents = Extents(df[xcol].min(),
                      df[ycol].min(),
                      df[xcol].max(),
                      df[ycol].max())

    return extents


def pad_extents(extents: Extents, pad: float = 0.05) -> Extents:
    """Pad an Extents by a factor

    """
    padx = (extents.maxx - extents.minx)*0.05
    pady = (extents.maxy - extents.miny)*0.05

    result = Extents(extents.minx - padx,
                     extents.miny - pady,
                     extents.maxx + padx,
                     extents.maxy + pady)

    return result


def cols_to_linecollection(
    df: pnd.DataFrame,
    xcol: str = 'x',
    ycol: str = 'y',
    style: Union[None, dict] = None
) -> LineCollection:
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
