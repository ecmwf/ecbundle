# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.


# Ideally, the YAML parser ruamel is preinstalled
# But if not, no panic, it is added as a contrib in this repository

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR + "/../contrib")


from ruamel.yaml import YAML
from ruamel.yaml.compat import StringIO


def parse_yaml_file(filepath):
    config = dict()
    with open(filepath, "r") as ymlfile:
        ymlstring = ymlfile.read()
        config = YAML().load(ymlstring)
    return config


def to_yaml_str(config):
    ostream = StringIO()
    YAML().dump(config, ostream)
    return ostream.getvalue()


def splitted(s):
    import re

    def replacer(m):
        return m.group(0).replace(" ", "\x00")

    parts = re.sub('".+?"', replacer, s).split()
    parts = [p.replace("\x00", " ") for p in parts]
    return parts
