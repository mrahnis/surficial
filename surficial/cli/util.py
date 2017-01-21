def load_style(styles_f):
    """Load a json file containing the keyword arguments to use for plot styling

    Parameters:
        styles_f: path to json file containing matplotlib style keyword arguments

    Returns:
        styles (dict): dictionary of matplotlib keyword arguments

    """
    import json

    with open(styles_f, 'r') as styles_src:
        styles = json.load(styles_src)
    return styles

def check_crs(source_crs, base_crs=None):
    """Check the crs for correctness

    Parameters:
        source_crs (str): coordinate reference system in well-known text (WKT) format

    Other Parameters:
        base_crs (str): coordinate reference system for comparison

    Returns:
        crs (SpatialReference): coordinate reference system of the source data
        status (str): status message

    """
    from gdal import osr

    crs=osr.SpatialReference(wkt=source_crs)
    if crs.IsProjected and base_crs == None:
        status = 'success'
    elif crs.IsProjected and crs == base_crs:
        status = 'success'
    elif crs.IsProjected and crs != base_crs:
        status = 'unequal'
    else:
        status = 'unprojected'

    return crs, status

def read_geometries(feature_f):
    """Read feature source geometries

    Parameters:
        feature_f: path to the feature data to read

    Returns:
        schema_geometry (str): feature type
        feature_crs (str): feature source crs in well-known text (WKT) format 
        geometries: list of shapely geometries

    """
    import click
    import fiona
    import rasterio
    from shapely.geometry import shape

    with fiona.open(feature_f) as feature_src:
        supported = ['Point', 'LineString', '3D Point', '3D LineString']
        schema_geometry = feature_src.schema['geometry'] 
        try:
            if schema_geometry not in supported:
                raise click.BadParameter('Geometry must be one of: {}'.format(supported))
        except:
            raise click.BadParameter('Unable to obtain schema from {}'.format(feature_f))
        geometries = [shape(feature['geometry']) for feature in feature_src]
        feature_crs = feature_src.crs_wkt
    return schema_geometry, feature_crs, geometries

"""
def read_geometries(feature_f, elevation_f=None, keep_z=False):

    import click
    import fiona
    import rasterio
    from shapely.geometry import shape

    import drapery

    with fiona.open(feature_f) as feature_src:
        supported = ['Point', 'LineString', '3D Point', '3D LineString']
        try:
            if feature_src.schema['geometry'] not in supported:
                raise click.BadParameter('Geometry must be one of: {}'.format(supported))
        except:
            raise click.BadParameter('Unable to obtain schema from {}'.format(feature_f))
        if elevation_f and not keep_z:
            with rasterio.open(elevation_f) as raster:
                if feature_src.crs != raster.crs:
                    raise click.BadParameter('{} and {} use different CRS'.format(feature_f, elevation_f))
                geometries = [drapery.drape(raster, feature) for feature in feature_src]
        else:
            if feature_src.schema['geometry'] in ['LineString', 'Point'] and not keep_z:
                raise click.BadParameter('{} is 2D. Provide an elevation source, or convert to 3D geometry'.format(feature_f))
            geometries = [shape(feature['geometry']) for feature in feature_src]

        feature_crs = feature_src.crs_wkt

    return feature_crs, geometries
"""


def df_extents(df, xcol='x', ycol='y'):
    from collections import namedtuple

    Extents = namedtuple('Extents', ['minx', 'miny', 'maxx', 'maxy'])

    extents = Extents(df[xcol].min(), df[ycol].min(), df[xcol].max(), df[ycol].max())
    return extents