"""
Test cases for twisted.hook module.
"""

from twisted.python import hook
from pyunit import unittest

class BaseClass:
    """
    dummy class to help in testing.
    """
    def __init__(self):
        """
        dummy initializer
        """
        self.calledBasePre = 0
        self.calledBasePost = 0
        self.calledBase = 0

    def func(self, a, b):
        """
        dummy method
        """
        assert a == 1
        assert b == 2
        self.calledBase = self.calledBase + 1


class SubClass(BaseClass):
    """
    another dummy class
    """
    def __init__(self):
        """
        another dummy initializer
        """
        BaseClass.__init__(self)
        self.calledSubPre = 0
        self.calledSubPost = 0
        self.calledSub = 0

    def func(self, a, b):
        """
        another dummy function
        """
        assert a == 1
        assert b == 2
        BaseClass.func(self, a, b)
        self.calledSub = self.calledSub + 1


def basePre(base, a, b):
    """
    a pre-hook for the base class
    """
    base.calledBasePre = base.calledBasePre + 1

def basePost(base, a, b):
    """
    a post-hook for the base class
    """
    base.calledBasePost = base.calledBasePost + 1

def subPre(sub, a, b):
    """
    a pre-hook for the subclass
    """
    sub.calledSubPre = sub.calledSubPre + 1

def subPost(sub, a, b):
    """
    a post-hook for the subclass
    """
    sub.calledSubPost = sub.calledSubPost + 1

class HookTestCase(unittest.TestCase):
    """
    test case to make sure hooks are called
    """
    def testBaseHook(self):
        """
        make sure that the base class's hook is called reliably
        """
        base = BaseClass()
        assert base.calledBase == 0
        assert base.calledBasePre == 0
        base.func(1,2)
        assert base.calledBase == 1
        assert base.calledBasePre == 0
        hook.addPre(BaseClass, "func", basePre)
        base.func(1, b=2)
        assert base.calledBase == 2
        assert base.calledBasePre == 1
        hook.addPost(BaseClass, "func", basePost)
        base.func(1, b=2)
        assert base.calledBasePost == 1
        assert base.calledBase == 3
        assert base.calledBasePre == 2
        hook.removePre(BaseClass, "func", basePre)
        hook.removePost(BaseClass, "func", basePost)
        base.func(1, b=2)
        assert base.calledBasePost == 1
        assert base.calledBase == 4
        assert base.calledBasePre == 2

    def testSubHook(self):
        """
        test interactions between base-class hooks and subclass hooks
        """
        sub = SubClass()
        assert sub.calledSub == 0
        assert sub.calledBase == 0
        sub.func(1, b=2)
        assert sub.calledSub == 1
        assert sub.calledBase == 1
        hook.addPre(SubClass, 'func', subPre)
        assert sub.calledSub == 1
        assert sub.calledBase == 1
        assert sub.calledSubPre == 0
        assert sub.calledBasePre == 0
        sub.func(1, b=2)
        assert sub.calledSub == 2
        assert sub.calledBase == 2
        assert sub.calledSubPre == 1
        assert sub.calledBasePre == 0
        # let the pain begin
        hook.addPre(BaseClass, 'func', basePre)
        BaseClass.func(sub, 1, b=2)
        # sub.func(1, b=2)
        assert sub.calledBase == 3
        assert sub.calledBasePre == 1, str(sub.calledBasePre)
        sub.func(1, b=2)
        assert sub.calledBasePre == 2
        assert sub.calledBase == 4
        assert sub.calledSubPre == 2
        assert sub.calledSub == 3

testCases = [HookTestCase]




