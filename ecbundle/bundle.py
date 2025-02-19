# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.

from .data import Data
from .option import Option
from .parse import parse_yaml_file, splitted, to_yaml_str
from .project import Project

__all__ = ["Bundle"]


class Bundle(object):
    """
    Definition of a Bundle of software projects that depend on each
    other and can be downloaded and compiled safely together.
    """

    def __init__(self, filepath, env=True):
        self.filepath = filepath
        self.config = parse_yaml_file(self.filepath)
        if env:
            self.environment_overwrite()

    def get(self, key, default=None):
        return self.config[key] if key in self.config else default

    def name(self):
        return self.get("name", default="bundle")

    def version(self):
        return str(self.get("version", default="0.0.0"))

    def languages(self):
        return self.get("languages")

    def cmake(self):
        if self.get("cmake"):
            split = [c.strip() for c in splitted(self.get("cmake"))]
            return [c for c in split if c]
        else:
            return []

    def projects(self):
        pconf = self.get("projects", [])
        return [
            Project(name=key, **dict(val.items()))
            for p in pconf
            for (key, val) in p.items()
        ]
        # Python 2:
        # return [Project(name=p.items()[0][0], **p.items()[0][1]) for p in pconf]

    def data(self):
        dconf = self.get("data", [])
        return [
            Data(name=key, **dict(val.items()))
            for d in dconf
            for (key, val) in d.items()
        ]
        # Python 2:
        # return [Data(name=d.items()[0][0], **d.items()[0][1]) for d in dconf]

    def options(self):
        optconf = self.get("options", [])
        return [
            Option(name=key, **dict(val.items()))
            for opt in optconf
            for (key, val) in opt.items()
        ]
        # Python 2:
        # return [Option(name=opt.items()[0][0], **opt.items()[0][1]) for opt in optconf]

    def populate_options(self):
        optconf = self.get("populate_options", [])
        return [
            Option(name=key, **dict(val.items()))
            for opt in optconf
            for (key, val) in opt.items()
        ]

    def file(self):
        return self.filepath

    def __str__(self):
        return str(self.config)

    def __repr__(self):
        return str(self.config)

    def yaml(self):
        return to_yaml_str(self.config)

    def environment_overwrite(self):
        import os

        BUNDLE = self.name().replace("-", "_").upper()

        skip_projects = []

        for i, p in enumerate(self.projects()):
            pname = p.name()
            PNAME = pname.replace("-", "_").upper()
            NAME = BUNDLE + "_" + PNAME

            pconf = self.config["projects"][i][p.name()]
            VERSION = NAME + "_VERSION"
            if os.getenv(VERSION):
                pconf["version"] = os.getenv(VERSION)

            CMAKE = NAME + "_CMAKE"
            if os.getenv(CMAKE):
                pconf["cmake"] = os.getenv(CMAKE)

            GIT = NAME + "_GIT"
            if os.getenv(GIT):
                pconf["git"] = os.getenv(GIT)

            SKIP = BUNDLE + "_SKIP_" + PNAME
            if os.getenv(SKIP):
                skip_projects.append(i)

            DIR = NAME + "_DIR"
            if os.getenv(DIR):
                pconf["dir"] = os.getenv(DIR)

        for i in reversed(skip_projects):
            self.config["projects"].pop(i)
