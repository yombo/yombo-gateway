import pyximport; pyximport.install()
from unittest import TestCase, main

from mock import Mock

from yombo.core.helpers import getComponent

from .. import ExpectingTestCase

class CronTabTests(ExpectingTestCase):
    """
    Test class for messages.
    """
    def setUp(self):
        self._CronTab = getComponent("yombo.gateway.lib.crontab")

    def testCreateCronJob(self):
        m = Mock()
        myCron = self._CronTab.new(m, label="MyCron")
        self.expectTrue(myCron.enabled, "CronJob should be enabled, but it's not.", first=True)
        self.expectEqual(myCron.label, "MyCron", "CronJob label wasn't set properly.")

    def testCreateCronWithTime(self):
        m = Mock()
        myCron = self._CronTab.new(m, min=1, hour=range(2, 12, 2), label="MyCron")
        self.expectSetEqual([1,], myCron.mins, "CronJob should run at 1 mins after the hour, but it's not.", first=True)
        self.expectSetEqual(range(2, 12, 2), myCron.hours, "CronJob should run at various hours, but it's not.")

    def testCreateRunAt(self):
        m = Mock()
        myCron = self._CronTab.run_at(m, "14:25")
        self.expectSetEqual([25,], myCron.mins, "CronJob should run at 25 mins after the hour, but it's not.", first=True)
        self.expectSetEqual([14,], myCron.hours, "CronJob should run at hour 14 (2pm), but it's not.")

    def testDisableThenEnableLocally(self):
        m = Mock()
        myCron = self._CronTab.new(m, label="MyCron")
        myCron.disable()
        self.expectFalse(myCron.enabled, "CronJob should be disabled, but it's not.", first=True)
        myCron.enable()
        self.expectTrue(myCron.enabled, "CronJob should be enabled, but it's not.1")

    def testDisableThenEnableThruCronTab(self):
        m = Mock()
        myCron = self._CronTab.new(m, label="MyCron")
        self._CronTab.disable(myCron.cronUUID)
        self.expectFalse(myCron.enabled, "CronJob should be disabled thru CronTab, but it's not.", first=True)
        self._CronTab.enable(myCron.cronUUID)
        self.expectTrue(myCron.enabled, "CronJob should be enabled thru CronTab, but it's not.")

    def testRunNowThruCronTab(self):
        m = Mock()
        myCron = self._CronTab.new(m, label="MyCron")
        self._CronTab.run_now(myCron.cronUUID)
        self.assertEqual(m.called, True, "CronTab called called run_now, but action function wasn't called!")

    def testRunNowThruCronTab(self):
        m = Mock()
        myCron = self._CronTab.new(m, label="MyCron")
        myCron.run_now()
        self.assertEqual(m.called, True, "CronJob called run_now, but action function wasn't called!")


if __name__ == '__main__':
    main()
