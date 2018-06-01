import numpy as np
import pandas as pnd


def knickpoint(vertices, min_slope, min_drop, up=True):
    """Identify knickpoints given minimum slope and elevation drop

    Shortcomings
    * the slope series of interest must be entirely within the graph edge
    * controlling it is fiddely by nature
    
    Parameters:
        vertices (DataFrame): vertex coordinates
        min_slope (float): slope as rise/run; negative slopes fall downstream
        min_drop (float): minimum elevation drop required for identification 
        up (boolean): return crest of slope (default) or toe of slope

    Returns:
        result (DataFrame): Datafrom records marking crest/toe of slopes meeting the given criteria with column for accumulated drop

        :m (float): distance from the edge start endpoint
        :x (float): x coordinate
        :y (float): y coordinate
        :z (float): z coordinate
        :edge (tuple): pair of graph nodes (from, to)
        :m_relative (float): distance from the outlet
        :zmin (float): z where spikes have been removed by expanding min
        :rise (float): change in specified column in the downstream direction
        :slope (float): rise over run in the downstream direction 
        :drop (float): max accumulated drop above min_drop over a slope steeper than min_slope

    """
    vertices['is_steep'] = np.where(vertices['slope'] <= min_slope, 0, 1)
    # okay as long as slope doesn't terminate at an endpoint - need to expand
    vertices['is_steep'] = vertices['is_steep'].shift(1)
    vertices['series'] = vertices['is_steep'].cumsum()

    ups = vertices.groupby('series').first()
    downs = vertices.groupby('series').last()
    drops = ups['zmin'] - downs['zmin']
    drops.name = 'drop'
    if up == True:
        candidates = pnd.concat([ups, drops], axis=1)
    else:
        candidates = pnd.concat([downs, drops], axis=1)
    result = candidates[candidates['drop'] >= min_drop]

    return result


def knickpoint_alt(vertices, min_slope, min_drop, up=True):
    """Identify knickpoints given minimum slope and elevation drop

    Shortcomings
    * the slope series of interest must be entirely within the graph edge
    * downstream direction slope series are not inclusive of the last point of the slope(?)
    * controlling it is fiddely by nature

    Parameters:
        vertices (DataFrame): vertex coordinates
        min_slope (float): slope as rise/run; negative slopes fall downstream
        min_drop (float): minimum threshold elevation drop to identify a dam or knickpoint
        up (boolean): return crest of slope (default) or toe of slope

    Returns:
        result (DataFrame): Datafrom records marking toe of slopes meeting the given criteria with column for accumulated drop

        :m (float): distance from the edge start endpoint
        :x (float): x coordinate
        :y (float): y coordinate
        :z (float): z coordinate
        :edge (tuple): pair of graph nodes (from, to)
        :m_relative (float): distance from the outlet
        :zmin (float): z where spikes have been removed by expanding min
        :rise (float): change in specified column in the downstream direction
        :slope (float): rise over run in the downstream direction
        :drop (float): max accumulated drop above min_drop over a slope steeper than min_slope

    """
    vertices['is_steep'] = np.where(vertices['slope'] <= min_slope, 0, 1)
    vertices['series'] = vertices['is_steep'].cumsum()
    if up == True:
        vertices['drop'] = vertices.sort_values(by='m_relative', ascending=True).groupby(['series'])['rise'].cumsum()
        idx_0 = vertices.groupby(['series'])['drop'].transform(max) == vertices['drop']
        hits_0 = vertices[idx_0]
        idx_1 = hits_0.groupby(['series'])['m_relative'].transform(max) == hits_0['m_relative']
        hits = hits_0[idx_1].drop(['is_steep', 'series'], axis=1)
    else:
        vertices['drop'] = vertices.groupby(['series'])['rise'].cumsum()
        idx = vertices.groupby(['series'])['drop'].transform(max) == vertices['drop']
        hits = vertices[idx].drop(['is_steep', 'series'], axis=1)
    result = hits[hits['drop'] >= min_drop]

    return result
