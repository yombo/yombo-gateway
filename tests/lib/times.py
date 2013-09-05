import pyximport; pyximport.install()
from unittest import TestCase, main

from yombo.lib.loader import setupLoader, getLoader
from yombo.core.helpers import getTimes,getComponent

class TimesTest(TestCase):

    def setUp(self):
        setupLoader()
        self._loader = getLoader()
        self._loader.importLibraries()
        self.times = getTimes()
        self.times.init(self._loader,PatchEnvironment=True)
        self.messages = getComponent('yombo.gateway.lib.messages')
        self.messages.init(self._loader)

    def test_something(self):
        self.times.run_inner_tests()
        self.moonrise = times.objRise(1, 'Moon') # 1 - we want the next moon rise
        print "**********************************************************************************************************************************************************************************"
        print "*************************************HERE WE STARTING TESTS -- ALL ERRORS ABOVE(about reactor) DO NOT MATTER*********************************************************************"
        print "moonrise = %s" % moonrise

if __name__ == '__main__':
    main() 

