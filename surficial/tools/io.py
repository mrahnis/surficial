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
        dictionary of matplotlib keyword arguments

    """

    with open(style, 'r') as styles_src:
        styles = json.load(styles_src)
    return styles


def read_crs(layer: str) -> tuple[str, CRS]:
    with fiona.open(layer) as feature_src:
        feature_crs = CRS.from_wkt(feature_src.crs_wkt)

    return feature_crs


def read_geometries(feature_src: str) -> list[tuple[str, Any]]:
    """Read feature source geometries

    Parameters:
        layer: path to the feature data to read

    Returns:
        feature geometry type, feature source crs as well-known text (WKT), shapely geometries

    """
    supported = ['Point', 'LineString', '3D Point', '3D LineString']
    try:
        if feature_src.schema['geometry'] not in supported:
            raise click.BadParameter('Geometry must be one of: {}'.format(supported))
    except:
        # raise click.BadParameter('Unable to obtain schema from {}'.format(layer))
        raise click.BadParameter('Unable to obtain schema from {}'.format(feature_src.schema['geometry']))

    features = [(feature.id, shape(feature['geometry'])) for feature in feature_src]

    return features


def read_attribute(layer: str) -> list[Any]:
    """Read feature attribute

    Parameters:
        layer: path to the feature data to read

    Returns:
        list of feature attribute

    """
    with fiona.open(layer) as feature_src:
        idx = [feature['id'] for feature in feature_src]
    return idx
