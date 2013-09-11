import pyximport; pyximport.install()
from unittest import TestCase, main

import sys
import os
import os.path

from yombo.lib.loader import setupLoader, getLoader
from yombo.core.helpers import *

class HelpersTests(TestCase):
    """
    Test class for messages.
    """
    def setUp(self):
        setupLoader()
        self._loader = getLoader()
        self._loader.importLibraries()

    def testgenerateRandom(self):
        self.assertEqual(len(generateRandom(), 32)

    def testgenerateRandomNewSize(self):
        self.assertEqual(len(generateRandom(length=40), 40)

    def testgenerateUUID(self):
        self.assertEqual(len(generateUUID(), 30)


if __name__ == '__main__':
    main()
