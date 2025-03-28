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
from .logging import debug, info
from .util import execute, fullpath

__all__ = ["CacheCreator"]


def get_populate_options(bundle, config):
    options = bundle.populate_options()
    return dict(
        (pop.split("=", 1)[0], pop.split("=", 1)[1])
        for opt in options
        for pop in opt.populate(config.get(opt.key(), None))
        if opt.key() in config
    )


class CacheCreator(object):
    def __init__(self, **kwargs):
        self.config = kwargs
        self.dryrun = self.config["dryrun"]
        self.capture_output = self.config.get("capture_output", False)
        self.log = debug if self.config.get("silent", False) else info

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
        options = get_populate_options(bundle, self.config)

        for project in bundle.projects():

            if project.populate():
                for pop in project.populate():
                    k, v = pop.split("=", 1)
                    opt = options.get(k, None)
                    if not opt or opt.replace('"', "") == "None":
                        options.update({k: v})

            create_cache = Path(self.src_dir()) / project.name() / "populate"
            if create_cache.is_file():
                # We also might want to capture the output of the populate script
                _output = execute(
                    str(create_cache),
                    dryrun=self.dryrun,
                    env=dict(os.environ, ARTIFACTS_DIR=self.artifacts_dir(), **options),
                    capture_output=self.capture_output,
                )
                if self.capture_output:
                    self.log(_output)
        return 0
