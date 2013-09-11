import pyximport; pyximport.install()
from unittest import TestCase, main
from yombo.core.auth import *

class AuthTests(TestCase):

    def setUp(self):
        pass

    def testValidateNonceTooShort(self):
        self.assertFalse(validateNonce('abcd'), 'ValidateNonce "asdf" should fail, too short.')

    def testValidateNonceNotRandom(self):
        self.assertFalse(validateNonce('asdfasdfasdfasdfasdfasdfasdfasdf'), 'ValidateNonce should fail, not rando enough.')

    def testValidateNonceIsValid(self):
        self.assertTrue(validateNonce('abcdefghijklmnopqrstuvwxyzABCDEF'), 'ValidateNonce should pass with long enough and random.')

    def testGenerateToken(self):
        # 34b2a2671d..  - precomputed
        self.assertEqual(generateToken("abcdefg", "123456", 'wxyz'), '34b2a2671d0d546ad7a46dc92c2a1937575e49c5e2a9d6fd4a3a36db6b660d79')

    def testCheckToken(self):
        self.assertTrue(checkToken('34b2a2671d0d546ad7a46dc92c2a1937575e49c5e2a9d6fd4a3a36db6b660d79', "abcdefg", "123456", 'wxyz'))

if __name__ == '__main__':
    main()

