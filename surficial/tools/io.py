from __future__ import annotations

from typing import Union, Any
import json

import click
import fiona
import rasterio
from pyproj.crs import CRS
from shapely.geometry import shape


def load_style(style: str) -> dict:
    """Load a json file containing the keyword arguments to use for plot styling

    Parameters:
        style: path to json file containing matplotlib style keyword arguments

    Returns:
        styles (dict): dictionary of matplotlib keyword arguments

    """

    with open(style, 'r') as styles_src:
        styles = json.load(styles_src)
    return styles


def read_geometries(layer: str) -> tuple[str, CRS, list[Any]]:
    """Read feature source geometries

    Parameters:
        layer: path to the feature data to read

    Returns:
        schema_geometry (str): feature type
        feature_crs (str): feature source crs in well-known text (WKT) format
        geometries: list of shapely geometries

    """
    with fiona.open(layer) as feature_src:
        supported = ['Point', 'LineString', '3D Point', '3D LineString']
        schema_geometry = feature_src.schema['geometry']
        try:
            if schema_geometry not in supported:
                raise click.BadParameter('Geometry must be one of: {}'.format(supported))
        except:
            raise click.BadParameter('Unable to obtain schema from {}'.format(layer))
        geometries = [shape(feature['geometry']) for feature in feature_src]
        feature_crs = CRS.from_wkt(feature_src.crs_wkt)
    return schema_geometry, feature_crs, geometries


def read_identifiers(layer: str) -> tuple[str, CRS, list[Any]]:
    """Read feature source geometries

    Parameters:
        layer: path to the feature data to read

    Returns:
        schema_geometry (str): feature type
        feature_crs (str): feature source crs in well-known text (WKT) format
        geometries: list of shapely geometries

    """
    with fiona.open(layer) as feature_src:
        supported = ['Point', 'LineString', '3D Point', '3D LineString']
        schema_geometry = feature_src.schema['geometry']
        try:
            if schema_geometry not in supported:
                raise click.BadParameter('Geometry must be one of: {}'.format(supported))
        except:
            raise click.BadParameter('Unable to obtain schema from {}'.format(layer))
        idx = [feature['id'] for feature in feature_src]
        feature_crs = CRS.from_wkt(feature_src.crs_wkt)
    return schema_geometry, feature_crs, idx
