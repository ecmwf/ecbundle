# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.

import os
from pathlib import Path

from .bundle import Bundle
from .util import execute, fullpath

__all__ = ["CacheCreator"]


class CacheCreator(object):
    def __init__(self, **kwargs):
        self.config = kwargs
        self.dryrun = self.config["dryrun"]

    def bundle(self):
        return Bundle(self.src_dir() + "/bundle.yml", env=False)

    def get(self, key, default=None):
        key = key.replace("-", "_")
        return self.config[key] if self.config.get(key) is not None else default

    def src_dir(self):
        return fullpath(self.get("src_dir", "source"))

    def artifacts_dir(self):
        return fullpath(self.get("artifacts_dir", self.src_dir() + "/artifacts"))

    def create(self):
        bundle = self.bundle()
        for project in bundle.projects():
            create_cache = Path(self.src_dir()) / project.name() / "populate"
            if create_cache.is_file():
                execute(
                    str(create_cache),
                    dryrun=self.dryrun,
                    env=dict(os.environ, ARTIFACTS_DIR=self.artifacts_dir()),
                )
        return 0
