#!/usr/bin/env python
import pyximport; pyximport.install()

import sys
import os
import os.path
from pprint import pprint as p

#sys.path.append(os.path.join("/home/mitch/yombo/projects/gateway", ""))
sys.path.append("/home/mitch/yombo/projects/gateway")
p(sys.path)

import unittest
from yombo.core.message import Message

ISTESTING = True


class testMessage(unittest.TestCase):
    """
    Test class for messages.
    """
    def setUp(self):
        """
        set up data used in the tests.
        setUp is called before each test function execution.
        """
        msg = {
               'msgOrigin'      : "test.unittest.Origin",
               'msgDestination' : "test.unittest.Destination",
               'msgType'        : "test", 
               'msgStatus'      : "new",
               'uuidType'       : "1",
               'uuidSubType'    : "123",
               'payload'        : {},
               }
        self.message = Message(**msg)        

    def testMsgOrigin(self):
        self.assertEqual(self.message.msgOrigin, "test.unittest.Origin")

    def testMsgDestination(self):
        self.assertEqual(self.message.msgDestination, "test.unittest.Destination")

if __name__ == '__main__':
    unittest.main()
