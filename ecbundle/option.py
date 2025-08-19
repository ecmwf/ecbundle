# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.

from .parse import splitted

__all__ = ["Option"]


class Option(object):
    """
    Definition of an option that is bespoke to an indivdual bundle
    and allows the definition of custom behaviour.
    """

    def __init__(self, **kwargs):
        self.config = kwargs

    def get(self, key, default=None):
        return self.config[key] if key in self.config else default

    def name(self):
        return self.get("name")

    def key(self):
        return self.get("name").replace("-", "_")

    def help(self):
        return self.get("help")

    def cmake(self, value=None):
        if self.get("cmake"):
            cmake_str = self.get("cmake")
            if "{{value}}" in cmake_str:
                cmake_str = cmake_str.replace("{{value}}", '"' + str(value) + '"')
            return splitted(cmake_str)
        else:
            return None

    def populate(self, value=None):
        if self.get("populate"):
            populate_str = self.get("populate")
            if "{{value}}" in populate_str:
                populate_str = populate_str.replace("{{value}}", '"' + str(value) + '"')
            return splitted(populate_str)
        else:
            return None

    def type(self):
        if self.get("type"):
            return self.get("type")
        if self.get("cmake"):
            cmake_str = self.get("cmake")
            if "{{value}}" in cmake_str:
                return "str"
        if self.get("populate"):
            populate_str = self.get("populate")
            if "{{value}}" in populate_str:
                return "str"
        return None

    def __str__(self):
        return str(self.config)

    def __repr__(self):
        return str(self.config)
