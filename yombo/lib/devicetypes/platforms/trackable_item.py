"""

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/devicetypes/platforms/trackable_item.html>`_
"""
from yombo.constants.features import FEATURE_ALLOW_IN_SCENES
from yombo.constants.platforms import PLATFORM_BASE_TRACKABLE_ITEM, PLATFORM_TRACKABLE_ITEM

from yombo.lib.devices.device import Device


class TrackableItem(Device):
    """
    A generic trackable item, such as a phone location or bluetooth tracker.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = PLATFORM_BASE_TRACKABLE_ITEM
        self.PLATFORM = PLATFORM_TRACKABLE_ITEM
        # Put two command machine_labels in a list to enable toggling.
        self.FEATURES[FEATURE_ALLOW_IN_SCENES] = False

    def toggle(self, **kwargs):
        return False

    def generate_human_state(self, machine_state, machine_state_extra):
        return "Unknown"  # TODO: Implement this.

