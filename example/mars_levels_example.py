#!/usr/bin/env python3
"""
Example program demonstrating how to use the MARS levtype/param to typeOfLevel mapping.

This script shows how to programmatically query the mappings both from the command line
and from within Python code.
"""

from ecbundle.mars_level_mapping import get_typeoflevel_for_levtype


def main():
    print("=" * 70)
    print("MARS levtype/param to GRIB typeOfLevel Mapping Examples")
    print("=" * 70)
    print()
    
    # Example 1: Surface data
    print("Example 1: Surface parameters")
    print("-" * 40)
    
    levtype = 'sfc'
    type_of_levels = get_typeoflevel_for_levtype(levtype)
    print(f"levtype='{levtype}' -> {type_of_levels}")
    
    params = ['2t', '2d', '10u', '10v', 'sp', 'msl']
    for param in params:
        type_of_levels = get_typeoflevel_for_levtype(levtype, param)
        print(f"levtype='{levtype}', param='{param:4s}' -> {type_of_levels}")
    print()
    
    # Example 2: Pressure levels
    print("Example 2: Pressure level parameters")
    print("-" * 40)
    
    levtype = 'pl'
    type_of_levels = get_typeoflevel_for_levtype(levtype)
    print(f"levtype='{levtype}' -> {type_of_levels}")
    
    params = ['t', 'u', 'v', 'z', 'q', 'r', 'w']
    for param in params:
        type_of_levels = get_typeoflevel_for_levtype(levtype, param)
        print(f"levtype='{levtype}', param='{param:4s}' -> {type_of_levels}")
    print()
    
    # Example 3: Model levels
    print("Example 3: Model level parameters")
    print("-" * 40)
    
    levtype = 'ml'
    type_of_levels = get_typeoflevel_for_levtype(levtype)
    print(f"levtype='{levtype}' -> {type_of_levels}")
    
    params = ['t', 'u', 'v', 'q', 'lnsp']
    for param in params:
        type_of_levels = get_typeoflevel_for_levtype(levtype, param)
        print(f"levtype='{levtype}', param='{param:4s}' -> {type_of_levels}")
    print()
    
    # Example 4: Ocean depth levels
    print("Example 4: Ocean depth parameters")
    print("-" * 40)
    
    levtype = 'od'
    type_of_levels = get_typeoflevel_for_levtype(levtype)
    print(f"levtype='{levtype}' -> {type_of_levels}")
    
    params = ['thetao', 'so', 'uo', 'vo']
    for param in params:
        type_of_levels = get_typeoflevel_for_levtype(levtype, param)
        print(f"levtype='{levtype}', param='{param:6s}' -> {type_of_levels}")
    print()
    
    print("=" * 70)
    print("To use from command line:")
    print("  ecbundle-mars-levels --levtype sfc --param 2t")
    print("  ecbundle-mars-levels --list-levtypes")
    print("  ecbundle-mars-levels --list-params")
    print("=" * 70)


if __name__ == '__main__':
    main()
