"""
Twisted Test Framework
"""

from twisted.python import reflect, log, failure
import sys, time, string, traceback, types, os, glob

log.startKeepingErrors()

class SkipTest(Exception):
    pass

class TestCase:
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def fail(self, message=None):
        raise AssertionError, message

    def failIf(self, condition, message=None):
        if condition:
            raise AssertionError, message

    def failUnless(self, condition, message=None):
        if not condition:
            raise AssertionError, message

    def failUnlessRaises(self, exception, f, *args, **kwargs):
        try:
            f(*args, **kwargs)
        except exception:
            return
        except:
            raise AssertionError, '%s raised instead of %s' % (sys.exc_info()[0], exception.__name__)
        else:
            raise AssertionError, '%s not raised' % exception.__name__

    def failUnlessEqual(self, first, second, msg=None):
        if not first == second:
            raise AssertionError, (msg or '%s != %s' % (first, second))

    def failIfEqual(self, first, second, msg=None):
        if not first != second:
            raise AssertionError, (msg or '%s == %s' % (first, second))

    assertEqual = assertEquals = failUnlessEqual
    assertNotEqual = assertNotEquals = failIfEqual
    assertRaises = failUnlessRaises
    assert_ = failUnless

    def assertApproximates(self, first, second, tolerance, msg=None):
        if abs(first - second) > tolerance:
            raise AssertionError, (msg or "%s ~== %s" % (first, second))


def isTestClass(testClass):
    return issubclass(testClass, TestCase)

def isTestCase(testCase):
    return isinstance(testCase, TestCase)

class TestSuite:
    methodPrefix = 'test'
    moduleGlob = 'test_*.py'
    
    def __init__(self):
        self.testClasses = {}
        self.numTests = 0
        self.couldNotImport = {}

    def getMethods(self, klass, prefix):
        testMethodNames = [ name for name in dir(klass)
                            if name[:len(prefix)] == prefix ]
        testMethodNames.sort()
        testMethods = [ getattr(klass, name) for name in testMethodNames
                        if type(getattr(klass, name)) is types.MethodType ]
        return testMethods

    def addTestClass(self, testClass):
        methods = self.getMethods(testClass, self.methodPrefix)
        self.testClasses[testClass] = methods
        self.numTests += len(methods)

    def addModule(self, module):
        if type(module) is types.StringType:
            try:
                module = reflect.namedModule(module)
            except ImportError:
                self.couldNotImport[module] = None
                return
        names = dir(module)
        for name in names:
            obj = getattr(module, name)
            if type(obj) is types.ClassType and isTestClass(obj):
                self.addTestClass(obj)

    def addPackage(self, packageName):
        try:
            package = reflect.namedModule(packageName)
        except ImportError:
            self.couldNotImport[packageName] = None
            return
        modGlob = os.path.join(os.path.dirname(package.__file__), self.moduleGlob)
        modules = map(reflect.filenameToModuleName, glob.glob(modGlob))
        for module in modules:
            self.addModule(module)

    def runOneTest(self, testClass, testCase, method, output):
        ok = 0
        try:
            testCase.setUp()
            method(testCase)
        except AssertionError, e:
            output.reportFailure(testClass, method, sys.exc_info())
        except KeyboardInterrupt:
            raise
        except SkipTest:
            output.reportSkip(testClass, method, sys.exc_info())
        except:
            output.reportError(testClass, method, sys.exc_info())
        else:
            ok = 1

        try:
            testCase.tearDown()
        except AssertionError, e:
            if ok:
                output.reportFailure(testClass, method, sys.exc_info())
            ok = 0
        except KeyboardInterrupt:
            raise
        except:
            if ok:
                output.reportError(testClass, method, sys.exc_info())
            ok = 0

        try:
            from twisted.internet import reactor
            reactor.iterate() # flush short-range timers
            pending = reactor.getDelayedCalls()
            if pending:
                msg = "\npendingTimedCalls still pending:\n"
                for p in pending:
                    msg += " %s\n" % p
                from warnings import warn
                warn(msg)
                for p in pending: p.cancel() # delete the rest
                reactor.iterate() # flush them
                # this will go live someday: tests should not leave
                # lingering surprises
                testCase.fail(msg)
        except AssertionError, e:
            if ok:
                output.reportFailure(testClass, method, sys.exc_info())
            ok = 0
        except KeyboardInterrupt:
            raise
        except:
            if ok:
                output.reportError(testClass, method, sys.exc_info())
            ok = 0

        for e in log.flushErrors():
            ok = 0
            output.reportError(testClass, method, e)

        if ok:
            output.reportSuccess(testClass, method)
        
    def run(self, output):
        output.start(self.numTests)
        testClasses = self.testClasses.keys()
        testClasses.sort(lambda x,y: cmp((x.__module__, x.__name__),
                                         (y.__module__, y.__name__)))
        for testClass in testClasses:
            testCase = testClass()
            for method in self.testClasses[testClass]:
                output.reportStart(testClass, method)
                self.runOneTest(testClass, testCase, method, output)
        for name in self.couldNotImport.keys():
            output.reportImportError(name)

        output.stop()

class Reporter:
    def __init__(self):
        self.errors = []
        self.failures = []
        self.imports = []
        self.skips = []
        self.numTests = 0
        self.expectedTests = 0

    def start(self, expectedTests):
        self.expectedTests = expectedTests
        self.startTime = time.time()

    def reportImportError(self, name):
        self.imports.append(name)

    def reportStart(self, testClass, method):
        pass

    def reportSkip(self, testClass, method, exc_info):
        self.skips.append((testClass, method, exc_info))
        self.numTests += 1

    def reportFailure(self, testClass, method, exc_info):
        self.failures.append((testClass, method, exc_info))
        self.numTests += 1

    def reportError(self, testClass, method, exc_info):
        self.errors.append((testClass, method, exc_info))
        self.numTests += 1

    def reportSuccess(self, testClass, method):
        self.numTests += 1

    def getRunningTime(self):
        if hasattr(self, 'stopTime'):
            return self.stopTime - self.startTime
        else:
            return time.time() - self.startTime

    def allPassed(self):
        return not (self.errors or self.failures)

    def stop(self):
        self.stopTime = time.time()

class TextReporter(Reporter):
    SEPARATOR = '-' * 79
    DOUBLE_SEPARATOR = '=' * 79
    
    def __init__(self, stream=sys.stdout):
        self.stream = stream
        Reporter.__init__(self)

    def reportFailure(self, testClass, method, exc_info):
        self.write('F')
        Reporter.reportFailure(self, testClass, method, exc_info)

    def reportError(self, testClass, method, exc_info):
        self.write('E')
        Reporter.reportError(self, testClass, method, exc_info)

    def reportSkip(self, testClass, method, exc_info):
        self.write('S')
        Reporter.reportSkip(self, testClass, method, exc_info)

    def reportSuccess(self, testClass, method):
        self.write('.')
        Reporter.reportSuccess(self, testClass, method)

    def _formatError(self, flavor, (testClass, method, error)):
        if isinstance(error, failure.Failure):
            tb = error.getBriefTraceback()
        else:
            tb = string.join(apply(traceback.format_exception, error))
            
        ret = ("%s\n%s: %s (%s)\n%s\n%s" %
               (self.DOUBLE_SEPARATOR,
                flavor, method.__name__, reflect.qual(testClass),
                self.SEPARATOR,
                tb))
        return ret

    def write(self, format, *args):
        if args:
            self.stream.write(format % args)
        else:
            self.stream.write(format)
        self.stream.flush()

    def writeln(self, format=None, *args):
        if format is not None:
            self.stream.write(format % args)
        self.stream.write('\n')
        self.stream.flush()

    def _statusReport(self):
        summaries = []
        if self.failures:
            summaries.append('failures=%d' % len(self.failures))
        if self.errors:
            summaries.append('errors=%d' % len(self.errors))
        if self.skips:
            summaries.append('skips=%d' % len(self.skips))
        summary = (summaries and ' ('+', '.join(summaries)+')') or ''
        if self.failures or self.errors:
            status = 'FAILED'
        else:
            status = 'OK'
        return '%s%s' % (status, summary)
            
    def stop(self):
        Reporter.stop(self)
        self.writeln()
        for error in self.failures:
            self.write(self._formatError('FAILURE', error))
        for error in self.errors:
            self.write(self._formatError('ERROR', error))
        for error in self.skips:
            self.write(self._formatError('SKIPPED', error))
        self.writeln(self.SEPARATOR)
        self.writeln('Ran %d tests in %.3fs', self.numTests, self.getRunningTime())
        self.writeln()
        self.writeln(self._statusReport())
        if self.imports:
            self.writeln()
            for name in self.imports:
                self.writeln('Could not import %s' % name)
            self.writeln()

class VerboseTextReporter(TextReporter):
    def __init__(self, stream=sys.stdout):
        TextReporter.__init__(self, stream)

    def reportStart(self, testCase, method):
        self.write('%s (%s) ... ', method.__name__, reflect.qual(testCase))

    def reportSuccess(self, testCase, method):
        self.writeln('[OK]')
        Reporter.reportSuccess(self, testCase, method)

    def reportFailure(self, testCase, method, exc_info):
        self.writeln('[FAIL]')
        Reporter.reportFailure(self, testCase, method, exc_info)

    def reportError(self, testCase, method, exc_info):
        self.writeln('[ERROR]')
        Reporter.reportError(self, testCase, method, exc_info)

    def reportSkip(self, testCase, method, exc_info):
        self.writeln('[SKIPPED]')
        Reporter.reportSkip(self, testCase, method, exc_info)

class TreeReporter(TextReporter):
    columns = 79

    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37
    
    def __init__(self, stream=sys.stdout):
        TextReporter.__init__(self, stream)
        self.lastModule = None
        self.lastClass = None

    def reportStart(self, testCase, method):
        if testCase.__module__ != self.lastModule:
            self.writeln(testCase.__module__)
            self.lastModule = testCase.__module__
        if testCase != self.lastClass:
            self.writeln('  %s' % testCase.__name__)
            self.lastClass = testCase
        self.currentLine = '    %s ... ' % method.__name__
        self.write(self.currentLine)

    def color(self, text, color):
        return '%s%s;1m%s%s0m' % ('\x1b[', color, text, '\x1b[')

    def endLine(self, message, color):
        import string
        spaces = ' ' * (self.columns - len(self.currentLine) - len(message))
        self.write(spaces)
        self.writeln(self.color(message, color))

    def reportSuccess(self, testCase, method):
        self.endLine('[OK]', self.GREEN)
        Reporter.reportSuccess(self, testCase, method)

    def reportFailure(self, testCase, method, exc_info):
        self.endLine('[FAIL]', self.RED)
        Reporter.reportFailure(self, testCase, method, exc_info)

    def reportError(self, testCase, method, exc_info):
        self.endLine('[ERROR]', self.RED)
        Reporter.reportError(self, testCase, method, exc_info)

    def reportSkip(self, testCase, method, exc_info):
        self.endLine('[SKIPPED]', self.BLUE)
        Reporter.reportSkip(self, testCase, method, exc_info)

def deferredResult(d, timeout=None):
    """Waits for a Deferred to arrive, then returns or throws an exception,
    based on the result.
    """
    
    from twisted.internet import reactor
    if timeout is not None:
        d.setTimeout(timeout)
    resultSet = []
    d.addCallbacks(resultSet.append, resultSet.append)
    while not resultSet:
        reactor.iterate()
    if isinstance(resultSet[0], failure.Failure):
        raise resultSet[0].value
    else:
        return resultSet[0]
    
