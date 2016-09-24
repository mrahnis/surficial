# using dask for out of core processing on large rasters
# https://gist.github.com/lpinner/bd57b54a5c6903e4a6a2

import rasterio
from shapely.geometry import Point, LineString

def add_height(raster, points):
    """
    Return the raster values at a given set of points.

    Parameters
    ----------
    raster (string) : path to a raster file supported by rasterio
    points (array of Point)

    Returns
    -------
    result (array of Point)

    """
    with rasterio.open(raster) as src:
        # better way than making LineString just to get coords?
        pts = LineString(points)
        zs = src.sample(pts.coords, indexes=src.indexes)
        result = [Point(p[0],p[1],z) for p, z in zip(pts.coords, zs)]
    return result

def add_height_line(raster, line):
    """
    Return the raster values at line vertices.

    Parameters
    ----------
    raster (string) : path to a raster file supported by rasterio
    line (LineString)

    Returns
    -------
    result (LineString)

    """
    # have to drop any existing Z information at coord[2] or sample will fail
    pts = LineString([Point(coord[0],coord[1]) for coord in line.coords])
    with rasterio.open(raster) as src:
        # better way than making a new LineString just to get coords?
        zs = src.sample(pts.coords, indexes=src.indexes)
        result = [Point(p[0],p[1],z) for p, z in zip(pts.coords, zs)]
    return LineString(result)
