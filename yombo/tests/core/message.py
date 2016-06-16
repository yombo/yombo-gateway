import pyximport; pyximport.install()
from unittest import TestCase, main

from yombo.core.message import Message

class MessageTests(TestCase):
    """
    Test class for messages.
    """
    def setUp(self):
        self.msg1 = {
               'msgOrigin'      : "yombo.gateway.lib.test",
               'msgDestination' : "yombo.gateway.lib.test",
               'msgType'        : "test", 
               'msgStatus'      : "new",
               'payload'        : {'cmd':'on', 'device':'desk lamp'},
               }
        self.message1 = Message(**self.msg1)        

    def testMsgOrigin(self):
        self.assertEqual(self.message1.msgOrigin, "yombo.gateway.lib.test")

    def testMsgDestination(self):
        self.assertEqual(self.message1.msgDestination, "yombo.gateway.lib.test")

    def testMsgUUID(self):
        self.assertTrue(hasattr(self.message1, 'msgUUID')) # asserIn doesn't appear to work

    def testMsgUUIDLength(self):
        self.assertEqual(len(self.message1.msgUUID), 30)

    def testMsgType(self):
        self.assertEqual(self.message1.msgType, "test")

    def testMsgPayloadType(self):
        self.assertIsInstance(self.message1.payload, dict)

    def testMsgPayloadTypeLength(self):
        self.assertEqual(len(self.message1.payload), 2)

    def testMsgPayloadTypeLength(self):
        self.assertEqual(len(self.message1.payload), 2)

    def testMsgReplyBasic(self):
        reply = self.message1.getReply()
        self.assertEqual(self.message1.msgUUID, reply.msgOrigUUID)

    def testMsgReplyStatus(self):
        reply = self.message1.getReply(msgStatus = 'failed')
        self.assertEqual(reply.msgStatus, 'failed')


if __name__ == '__main__':
    main()
