# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Class to hold images.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
from time import time


class Image(object):
    """Represent an image."""
    def __init__(self, content_type, image, created_at=None):
        self.content_type = content_type
        self.content = image
        self.created_at = created_at or time()
