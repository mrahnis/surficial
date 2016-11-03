def load_style(styles_f):
    """
    Load a json file containing the keyword arguments to use for plot styling
    """
    import json

    with open(styles_f, 'r') as styles_src:
        styles = json.load(styles_src)
    return styles

def read_geometries(feature_f, elevation_f=None, keep_z=False):
    """
    Read and drape line geometries
    """
    import click
    import fiona
    import rasterio
    from shapely.geometry import shape

    import drapery

    with fiona.open(feature_f) as feature_src:
        supported = ['Point', 'LineString', '3D Point', '3D LineString']
        if feature_src.schema['geometry'] not in supported:
            raise click.BadParameter('Geometry must be one of: {}'.format(supported))
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

