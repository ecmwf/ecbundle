#!/usr/bin/env python3

# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.

"""
Tests for MARS levtype to typeOfLevel mapping functionality.
"""

import pytest
from ecbundle.mars_level_mapping import (
    get_typeoflevel_for_levtype,
    get_all_levtypes,
    get_all_param_combinations,
)


def test_surface_levtype():
    """Test basic surface levtype mapping."""
    result = get_typeoflevel_for_levtype('sfc')
    assert result == ['surface']


def test_pressure_level_levtype():
    """Test pressure level mapping."""
    result = get_typeoflevel_for_levtype('pl')
    assert 'isobaricInhPa' in result
    assert 'isobaricInPa' in result


def test_model_level_levtype():
    """Test model level mapping."""
    result = get_typeoflevel_for_levtype('ml')
    assert result == ['hybrid']


def test_2m_temperature():
    """Test 2m temperature parameter-specific mapping."""
    result = get_typeoflevel_for_levtype('sfc', '2t')
    assert result == ['heightAboveGround']


def test_surface_pressure():
    """Test surface pressure parameter-specific mapping."""
    result = get_typeoflevel_for_levtype('sfc', 'sp')
    assert result == ['surface']


def test_pressure_level_temperature():
    """Test pressure level temperature mapping."""
    result = get_typeoflevel_for_levtype('pl', 't')
    assert result == ['isobaricInhPa']


def test_model_level_wind():
    """Test model level wind component mapping."""
    result = get_typeoflevel_for_levtype('ml', 'u')
    assert result == ['hybrid']


def test_ocean_depth_temperature():
    """Test ocean depth temperature mapping."""
    result = get_typeoflevel_for_levtype('od', 'thetao')
    assert result == ['depthBelowSea']


def test_unknown_levtype():
    """Test that unknown levtype returns empty list."""
    result = get_typeoflevel_for_levtype('unknown')
    assert result == []


def test_unknown_param():
    """Test that unknown param falls back to levtype mapping."""
    result = get_typeoflevel_for_levtype('sfc', 'unknown_param')
    assert result == ['surface']


def test_get_all_levtypes():
    """Test getting all levtypes."""
    levtypes = get_all_levtypes()
    assert isinstance(levtypes, list)
    assert 'sfc' in levtypes
    assert 'pl' in levtypes
    assert 'ml' in levtypes
    assert len(levtypes) > 0


def test_get_all_param_combinations():
    """Test getting all parameter combinations."""
    combinations = get_all_param_combinations()
    assert isinstance(combinations, list)
    assert ('sfc', '2t') in combinations
    assert ('pl', 't') in combinations
    assert ('ml', 'u') in combinations
    assert len(combinations) > 0


def test_param_specific_overrides_levtype():
    """Test that parameter-specific mapping overrides levtype mapping."""
    # Without param, should get generic surface mapping
    result_generic = get_typeoflevel_for_levtype('sfc')
    assert result_generic == ['surface']
    
    # With '2t' param, should get heightAboveGround
    result_specific = get_typeoflevel_for_levtype('sfc', '2t')
    assert result_specific == ['heightAboveGround']
    
    # These should be different
    assert result_generic != result_specific


def test_potential_vorticity_levtype():
    """Test potential vorticity levtype mapping."""
    result = get_typeoflevel_for_levtype('pv')
    assert 'theta' in result
    assert 'potentialVorticity' in result


def test_ocean_surface_levtype():
    """Test ocean surface levtype mapping."""
    result = get_typeoflevel_for_levtype('o2d')
    assert 'oceanSurface' in result or 'meanSea' in result


def test_wave_levtype():
    """Test wave levtype mapping."""
    result = get_typeoflevel_for_levtype('wave')
    assert 'surface' in result or 'meanSea' in result
