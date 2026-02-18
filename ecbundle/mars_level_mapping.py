#!/usr/bin/env python3

# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.

"""
MARS levtype to GRIB typeOfLevel mapping utility.

This module provides mappings between MARS levtype/param combinations
and their corresponding GRIB typeOfLevel values.
"""

# Mapping of MARS levtype to possible GRIB typeOfLevel values
LEVTYPE_TO_TYPEOFLEVEL = {
    'sfc': ['surface'],
    'pl': ['isobaricInhPa', 'isobaricInPa'],
    'ml': ['hybrid'],
    'pt': ['theta', 'potentialVorticity'],
    'pv': ['theta', 'potentialVorticity'],
    'o2d': ['oceanSurface', 'meanSea'],
    'od': ['depthBelowSea', 'depthBelowSeaFloor'],
    'wave': ['surface', 'meanSea'],
    'sol': ['surface', 'depthBelowLand'],
}

# Special parameter-specific mappings
# Some parameters may have specific typeOfLevel values depending on context
PARAM_SPECIFIC_MAPPINGS = {
    # Surface parameters
    ('sfc', '2t'): ['heightAboveGround'],  # 2m temperature
    ('sfc', '2d'): ['heightAboveGround'],  # 2m dewpoint
    ('sfc', '10u'): ['heightAboveGround'],  # 10m u-wind
    ('sfc', '10v'): ['heightAboveGround'],  # 10m v-wind
    ('sfc', 'sp'): ['surface'],  # Surface pressure
    ('sfc', 'msl'): ['meanSea'],  # Mean sea level pressure
    ('sfc', 'sst'): ['surface'],  # Sea surface temperature
    ('sfc', 'lsm'): ['surface'],  # Land-sea mask
    ('sfc', 'z'): ['surface'],  # Geopotential
    ('sfc', 'stl1'): ['depthBelowLandLayer'],  # Soil temperature level 1
    ('sfc', 'swvl1'): ['depthBelowLandLayer'],  # Soil moisture level 1
    
    # Pressure level parameters
    ('pl', 't'): ['isobaricInhPa'],  # Temperature
    ('pl', 'u'): ['isobaricInhPa'],  # U-wind
    ('pl', 'v'): ['isobaricInhPa'],  # V-wind
    ('pl', 'z'): ['isobaricInhPa'],  # Geopotential
    ('pl', 'q'): ['isobaricInhPa'],  # Specific humidity
    ('pl', 'r'): ['isobaricInhPa'],  # Relative humidity
    ('pl', 'w'): ['isobaricInhPa'],  # Vertical velocity
    
    # Model level parameters
    ('ml', 't'): ['hybrid'],  # Temperature
    ('ml', 'u'): ['hybrid'],  # U-wind
    ('ml', 'v'): ['hybrid'],  # V-wind
    ('ml', 'q'): ['hybrid'],  # Specific humidity
    ('ml', 'lnsp'): ['hybrid'],  # Log surface pressure
    
    # Potential temperature parameters
    ('pt', 'pv'): ['potentialVorticity'],  # Potential vorticity
    ('pt', 'u'): ['theta'],  # U-wind on theta
    ('pt', 'v'): ['theta'],  # V-wind on theta
    
    # Ocean parameters
    ('od', 'thetao'): ['depthBelowSea'],  # Ocean temperature
    ('od', 'so'): ['depthBelowSea'],  # Salinity
    ('od', 'uo'): ['depthBelowSea'],  # Eastward velocity
    ('od', 'vo'): ['depthBelowSea'],  # Northward velocity
}


def get_typeoflevel_for_levtype(levtype, param=None):
    """
    Get possible typeOfLevel values for a given MARS levtype and parameter.
    
    Args:
        levtype (str): MARS levtype (e.g., 'sfc', 'pl', 'ml', 'pt', 'pv', 'od', 'wave')
        param (str, optional): MARS parameter code (e.g., '2t', 't', 'u', 'sp')
        
    Returns:
        list: List of possible GRIB typeOfLevel values
        
    Examples:
        >>> get_typeoflevel_for_levtype('sfc')
        ['surface']
        >>> get_typeoflevel_for_levtype('sfc', '2t')
        ['heightAboveGround']
        >>> get_typeoflevel_for_levtype('pl')
        ['isobaricInhPa', 'isobaricInPa']
    """
    # First check for parameter-specific mapping
    if param:
        key = (levtype, param)
        if key in PARAM_SPECIFIC_MAPPINGS:
            return PARAM_SPECIFIC_MAPPINGS[key]
    
    # Fall back to general levtype mapping
    if levtype in LEVTYPE_TO_TYPEOFLEVEL:
        return LEVTYPE_TO_TYPEOFLEVEL[levtype]
    
    # If no mapping found, return empty list
    return []


def get_all_levtypes():
    """
    Get all available MARS levtype values.
    
    Returns:
        list: List of all known MARS levtype values
    """
    return sorted(LEVTYPE_TO_TYPEOFLEVEL.keys())


def get_all_param_combinations():
    """
    Get all known parameter-specific combinations.
    
    Returns:
        list: List of tuples (levtype, param)
    """
    return sorted(PARAM_SPECIFIC_MAPPINGS.keys())
