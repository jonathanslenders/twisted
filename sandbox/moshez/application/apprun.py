
# Copyright (C) 2001 Matthew W. Lefkowitz
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of version 2.1 of the GNU Lesser General Public
# License as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from twisted.python import runtime, log, usage
from twisted.persisted import styles
from twisted.application import persist
from twisted import copyright
import sys, os, pdb, profile, getpass, md5, traceback

reactorTypes = {
    'gtk': 'twisted.internet.gtkreactor',
    'gtk2': 'twisted.internet.gtk2reactor',
    'glade': 'twisted.internet.gladereactor',
    'default': 'twisted.internet.default',
    'win32': 'twisted.internet.win32eventreactor',
    'win': 'twisted.internet.win32eventreactor',
    'poll': 'twisted.internet.pollreactor',
    'qt': 'twisted.internet.qtreactor',
    'c' : 'twisted.internet.cReactor',
    'kqueue': 'twisted.internet.kqreactor'
    }


class EverythingEphemeral(styles.Ephemeral):
    def __getattr__(self, key):
        try:
            return getattr(mainMod, key)
        except AttributeError:
            if initRun:
                raise
            else:
                log.msg("Warning!  Loading from __main__: %s" % key)
                return styles.Ephemeral()

def createApplicationDecoder(config):
    mode = 'r'
    filename = os.path.abspath(config['python'] or config['xml'] or
                               config['source'] or config['file'])
    if config['python']:
        def decode(filename, data):
            d = {'__file__': filename}
            exec data in d, d
            try:
                return d['application']
            except KeyError:
                raise RuntimeError(
                        "Error - python file %r must set a variable named "
                        "'application', which implements the Application "
                        "protocol. No such variable was found!" % filename)
    else:
        if config['xml']:
            from twisted.persisted.marmalade import unjellyFromXML as load
        elif config['source']:
            from twisted.persisted.aot import unjellyFromSource as load
        else:
            from cPickle import load
            mode = 'rb'
        mainMod = sys.modules['__main__']
        def decode(filename, data):
            sys.modules['__main__'] = EverythingEphemeral()
            application = load(StringIO.StringIO(data))
            sys.modules['__main__'] = mainMod
            styles.doUpgrade()
            return application
    return filename, decode, mode


def loadApplication(config, passphrase):
    filename, decode, mode = createApplicationDecoder(config)
    if config['encrypted']:
        mode = 'rb'
    data = open(filename, mode).read()
    if config['encrypted']:
        data = persist.decrypt(passphrase, data)
    try:
        log.msg("Loading %s..." % (filename,))
        d = decode(filename, data)
        log.msg("Loaded.")
        return d
    except:
        if config['encrypt']:
            log.msg("Error loading Application - "
                    "perhaps you used the wrong passphrase?")
        raise

def installReactor(reactor):
    if reactor:
        reflect.namedModule(reactorTypes[reactor]).install()

def runReactor(config, oldstdout, oldstderr):
    from twisted.internet import reactor
    if config['profile']:
        p = profile.Profile()
        p.runctx("reactor.run()", globals(), locals())
        if config['savestats']:
            p.dump_stats(config['profile'])
        else:
            # XXX - omfg python sucks
            tmp, sys.stdout = sys.stdout, open(config['profile'], 'a')
            p.print_stats()
            sys.stdout, tmp = tmp, sys.stdout
            tmp.close()
    elif config['debug']:
        failure.startDebugMode()
        sys.stdout = oldstdout
        sys.stderr = oldstderr
        if runtime.platformType == 'posix':
            signal.signal(signal.SIGINT, lambda *args: pdb.set_trace())
        pdb.run("reactor.run()", globals(), locals())
    else:
        reactor.run()

def runReactorWithLogging(config, oldstdout, oldstderr):
    try:
        runReactor(config, oldstdout, oldstderr)
    except:
        if config['nodaemon']:
            file = oldstdout
        else:
            file = open("TWISTD-CRASH.log",'a')
        traceback.print_exc(file=file)
        file.flush()


def getPassphrase(needed):
    if needed:
        return getpass.getpass('Passphrase: ')
    else:
        return None

def getApplication(config, passphrase):
    global initRun
    initRun = 0
    try:
        application = loadApplication(config, passphrase)
    except Exception, e:
        s = "Failed to load application: %s" % (e,)
        traceback.print_exc(file=log.logfile)
        log.msg(s)
        log.deferr()
        sys.exit('\n' + s + '\n')
    initRun = 1
    return application

def reportProfile(report_profile, name):
    if name:
        from twisted.python.dxprofile import report
        log.msg("Sending DXP stats...")
        report(report_profile, name)
        log.msg("DXP stats sent.")
    else:
        log.err("--report-profile specified but application has no "
                "name (--appname unspecified)")

class ServerOptions(usage.Options):

    optFlags = [['savestats', None,
                 "save the Stats object rather than the text output of "
                 "the profiler."],
                ['debug', 'b',
                 "run the application in the Python Debugger "
                 "(implies nodaemon), sending SIGINT will drop into debugger"],
                ['quiet','q',     "be a little more quiet"],
                ['no_save','o',   "do not save state on shutdown"],
                ['encrypted', 'e',
                 "The specified tap/aos/xml file is encrypted."]]

    optParameters = [['logfile','l', None,
                      "log to a specified file, - for stdout"],
                     ['profile', 'p', None,
                      "Run in profile mode, dumping results to specified file"],
                     ['file','f','twistd.tap',
                      "read the given .tap file"],
                     ['python','y', None,
                      "read an application from within a Python file"],
                     ['xml', 'x', None,
                      "Read an application from a .tax file "
                      "(Marmalade format)."],
                     ['source', 's', None,
                      "Read an application from a .tas file (AOT format)."],
                     ['rundir','d','.',
                      'Change to a supplied directory before running'],
                     ['reactor', 'r', None,
                      'Which reactor to use out of: %s.' %
                      ', '.join(reactorTypes.keys())],
                     ['report-profile', None, None,
                      'E-mail address to use when reporting dynamic execution '
                      'profiler stats.  This should not be combined with '
                      'other profiling options.  This will only take effect '
                      'if the application to be run has an application '
                      'name.']]

    def opt_spew(self):
        """Print an insanely verbose log of everything that happens.  Useful
        when debugging freezes or locks in complex code."""
        sys.settrace(util.spewer)


def run(runApp, ServerOptions):
    # make default be "--help"
    if len(sys.argv) == 1:
        sys.argv.append("--help")

    config = ServerOptions()
    try:
        config.parseOptions()
    except usage.error, ue:
        config.opt_help()
        print "%s: %s" % (sys.argv[0], ue)
        os._exit(1)
    runApp(config)

def initialLog():
    from twisted.internet import reactor
    log.msg("twistd %s (%s %s) starting up" % (copyright.version,
                                               sys.executable,
                                               runtime.shortPythonVersion()))
    log.msg('reactor class: %s' % reactor.__class__)
