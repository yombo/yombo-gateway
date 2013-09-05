import pyximport; pyximport.install()
from unittest import TestCase, main

import sys
import os
import os.path

from yombo.lib.loader import setupLoader, getLoader
from yombo.core.helpers import getComponent
from yombo.core.message import Message

class MessageTests(TestCase):
    """
    Test class for messages.
    """
    def setUp(self):
        setupLoader()
        self._loader = getLoader()
        self._loader.importLibraries()
        self.msg1 = {
               'msgOrigin'      : "yombo.gateway.lib.test",
               'msgDestination' : "yombo.gateway.lib.test",
               'msgType'        : "test", 
               'msgStatus'      : "new",
               'payload'        : {},
               }
        self.message1 = Message(**self.msg1)        


    def testMsgOrigin(self):
        self.assertEqual(self.message1.msgOrigin, "yombo.gateway.lib.test")

    def testMsgDestination(self):
        self.assertEqual(self.message1.msgDestination, "yombo.gateway.lib.test")

    def testMsgUUID(self):
        self.assertTrue(hasattr(self.message1, 'msgUUID')) # asserIn doesn't appear to work
        self.assertEqual(len(self.message1.msgUUID), 30)

if __name__ == '__main__':
    main()
