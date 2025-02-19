# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.

import os

from .parse import splitted

__all__ = ["Project"]


class Project(object):
    """
    Definition of an individual Project in a Bundle that refers to a
    single source code defined either by a repository or a distinct
    sub-directory of a repository.
    """

    def __init__(self, **kwargs):
        # Expand values of environment variables for all options
        self.config = {
            k: os.path.expandvars(v) if isinstance(v, str) else v
            for k, v in kwargs.items()
        }

    def get(self, key, default=None):
        return self.config[key] if key in self.config else default

    def name(self):
        return self.get("name")

    def version(self):
        return str(self.get("version"))

    def git(self):
        return self.get("git")

    def remote(self):
        return self.get("remote", "origin")

    def submodules(self):
        return self.get("submodules", False)

    def cmake(self):
        if self.get("cmake"):
            split = [c.strip() for c in splitted(self.get("cmake"))]
            return [c for c in split if c]
        else:
            return None

    def populate(self):
        if self.get("populate"):
            split = [c.strip() for c in splitted(self.get("populate"))]
            return [c for c in split if c]
        else:
            return None

    def dir(self):
        return self.get("dir")

    def subdir(self):
        return self.get("subdir")

    def bundle(self):
        return self.get("bundle", default=True)

    def require(self):
        if self.get("require"):
            return self.get("require").split(" ")
        else:
            return None

    def optional(self):
        return self.get("optional", False)

    def __str__(self):
        return str(self.config)

    def __repr__(self):
        return str(self.config)
