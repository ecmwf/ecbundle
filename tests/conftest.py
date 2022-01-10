import logging
import sys
from io import StringIO


class Watcher(object):
    """
    ContextManager to redirect stdout and store result in an internalized string.

    If a logger is provided during construction we intercept logger messages as well.
    """

    def __init__(self, logger=None):
        self.logger = logger
        self.handler = None

    def __enter__(self, *args, **kwargs):
        """
        Stash stdout and replace with string-capture object.
        """
        self.f = StringIO()
        self._stdout = sys.stdout
        sys.stdout = self.f

        if self.logger:
            self.handler = logging.StreamHandler(self.f)
            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(self.handler)

    def __exit__(self, *args, **kwargs):
        """
        Reinstate stdout and flush our stored output.
        """
        sys.stdout = self._stdout
        self.output = self.f.getvalue()

        if self.logger:
            self.logger.removeHandler(self.handler)

        print(self.output)
