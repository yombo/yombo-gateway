import pyximport; pyximport.install()
from yombo.core.helpers import *

from .. import ExpectingTestCase

class HelpersTests(ExpectingTestCase):

    def testgenerateRandom(self):
        self.expectEqual(len(generateRandom()), 32)

    def testgenerateRandomNewSize(self):
        self.expectEqual(len(generateRandom(length=40)), 40)

    def testgenerateUUID(self):
        self.expectEqual(len(generateUUID()), 30)


if __name__ == '__main__':
    main()
