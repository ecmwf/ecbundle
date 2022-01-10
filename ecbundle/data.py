# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.

__all__ = ["Data"]


class Data(object):
    """
    Definition of an individual dataset downloadable from a URL.
    """

    def __init__(self, **kwargs):
        self.config = kwargs

    def get(self, key, default=None):
        return self.config[key] if key in self.config else default

    def name(self):
        return self.get("name")

    def url(self):
        return self.get("url")

    def MD5(self):
        return self.get("MD5")
