import pyximport; pyximport.install()
from unittest import TestCase, result
from unittest.case import _AssertRaisesContext
import sys

from yombo.lib.loader import setup_loader, get_loader

setup_loader(testing=True)
_loader = get_loader()
_loader.import_libraries()
#_getComponent = getComponent

class ExpectingTestCase(TestCase):
    def run(self, result=None):
        self._result = result
        self._num_expectations = 0
        super(ExpectingTestCase, self).run(result)

    def _fail(self, failure):
        try:
            raise failure
        except failure.__class__:
            self._result.addFailure(self, sys.exc_info())

    def expectRaises(self, excClass, callableObj=None, *args, **kwargs):
        context = _AssertRaisesContext(excClass, self)
        if callableObj is None:
            return context
        with context:
            callableObj(*args, **kwargs)

        self._result.testsRun += 1
        self._num_expectations += 1

    def expectTrue(self, a, msg='', first=False):
        if not a:
            self._fail(self.failureException(msg))
        elif not first:
          self._result.testsRun += 1
        self._num_expectations += 1

    def expectFalse(self, a, msg='', first=False):
        if a:
            self._fail(self.failureException(msg))
        elif not first:
          self._result.testsRun += 1
        self._num_expectations += 1

    def expectEqual(self, a, b, msg='', first=False):
        if a != b:
            msg = '(Test:{}) Expected "{}" to equal "{}". '.format(self._num_expectations, a, b) + msg
            self._fail(self.failureException(msg))
        elif not first:
          self._result.testsRun += 1
        self._num_expectations += 1

    def expectSetEqual(self, a, b, msg='', first=False):
        if set(a) != set(b):
            self._fail(self.failureException(msg))
        elif not first:
          self._result.testsRun += 1
        self._num_expectations += 1

from .lib import *
from .core import *
