import yombo.core.auth
from twisted.trial import unittest

class CoreAuthTestCase(unittest.TestCase):

    def test_generateNonce(self):
        nonce = generateNonce()
        print nonce
        self.assertEqual(result, 11)

