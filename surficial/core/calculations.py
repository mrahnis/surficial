
import pandas as pnd
import networkx as nx


def remove_spikes_edgewise(vertices: pnd.DataFrame) -> pnd.DataFrame:
    """Remove spikes by calculating an expanding minimum from upstream to downstream

    Adds a DataFrame column, zmin, to hold the despiked z-values.

    Parameters:
        vertices (DataFrame): vertex coordinates

    Returns:
        result (DataFrame): vertex coordinates with min column

    """
    grouped = vertices.groupby('edge')
    zmin = grouped['z'].apply(lambda x: x.expanding().min())
    zmin.name = 'zmin'

    result = pnd.concat([vertices, zmin], axis=1)

    return result


def rolling_mean_edgewise(points: pnd.DataFrame) -> pnd.DataFrame:
    """Calculate a rolling mean on a series of point z values

    Parameters:
        points (DataFrame): coordinate addresses

    Returns:
        result (DataFrame): coordinate addresses with mean column
    """
    grouped = points.groupby('edge')
    means = grouped['z'].apply(lambda x: x.rolling(window=9, win_type='triang', center=True).mean())
    means.name = 'zmean'

    result = pnd.concat([points, means], axis=1)

    return result


def difference(
    series1: pnd.DataFrame,
    series2: pnd.DataFrame,
    column1: str = 'zmean',
    column2: str = 'zmin'
) -> pnd.DataFrame:
    """Calculate the difference between zmin and zmean

    Parameters:
        series1 (DataFrame): first series
        series2 (DataFrame): second series
        column1 (string): first series column
        column2 (string): second series column

    """
    combined = pnd.concat([series1, series2], axis=0, ignore_index=True)
    grouped = combined.groupby('edge')
    for edge, group in grouped:
        aligned = group.sort_values(by='m')
        aligned_m = aligned.set_index('m')
        filled_series = aligned_m.interpolate(method='values')
        filled_series['diff'] = filled_series[column1] - filled_series[column2]
