def load_style(style):
    """Load a json file containing the keyword arguments to use for plot styling

    Parameters:
        style: path to json file containing matplotlib style keyword arguments

    Returns:
        styles (dict): dictionary of matplotlib keyword arguments

    """
    import json

    with open(style, 'r') as styles_src:
        styles = json.load(styles_src)
    return styles


def check_crs(layer_crs, base_crs=None):
    """Check the crs for correctness

    Parameters:
        layer_crs (str): coordinate reference system in well-known text (WKT) format

    Other Parameters:
        base_crs (str): coordinate reference system for comparison

    Returns:
        crs (SpatialReference): coordinate reference system of the source data
        status (str): status message

    """
    from gdal import osr

    crs = osr.SpatialReference(wkt=layer_crs)
    if crs.IsProjected and base_crs == None:
        status = 'success'
    elif crs.IsProjected and crs == base_crs:
        status = 'success'
    elif crs.IsProjected and crs != base_crs:
        status = 'unequal'
    else:
        status = 'unprojected'

    return crs, status


def read_geometries(layer):
    """Read feature source geometries

    Parameters:
        layer: path to the feature data to read

    Returns:
        schema_geometry (str): feature type
        feature_crs (str): feature source crs in well-known text (WKT) format
        geometries: list of shapely geometries

    """
    import click
    import fiona
    import rasterio
    from shapely.geometry import shape

    with fiona.open(layer) as feature_src:
        supported = ['Point', 'LineString', '3D Point', '3D LineString']
        schema_geometry = feature_src.schema['geometry']
        try:
            if schema_geometry not in supported:
                raise click.BadParameter('Geometry must be one of: {}'.format(supported))
        except:
            raise click.BadParameter('Unable to obtain schema from {}'.format(layer))
        geometries = [shape(feature['geometry']) for feature in feature_src]
        feature_crs = feature_src.crs_wkt
    return schema_geometry, feature_crs, geometries
