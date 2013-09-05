import pyximport; pyximport.install()
from unittest import TestCase, main
from yombo.core.auth import *

class AuthTests(TestCase):

    def testAuth(self):
        self.assertFalse(validateNonce('abcd'), 'ValidateNonce "asdf" should fail, too short.')
        self.assertFalse(validateNonce('asdfasdfasdfasdfasdfasdfasdfasdf'), 'ValidateNonce should fail, not rando enough.')
        self.assertTrue(validateNonce('abcdefghijklmnopqrstuvwxyzABCDEF'), 'ValidateNonce should pass with long enough and random.')
