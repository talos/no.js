import subprocess
import redis
import time
import logging
import sys

if sys.version.find('2.7') == 0:
    import unittest
elif sys.version.find('2.6') == 0:
    import unittest2 as unittest
else:
    print "Python %s not tested with opengold.  Use 2.6 or 2.7." % sys.version

#from threading import Thread

try:
    import opengold
except:
    ## if opengold is not installed, look for it manually.
    sys.path.extend(['../', '.'])

from opengold import deck, game

logging.basicConfig()
LOG = logging.getLogger('opengold')

# def logged_popen(*args, **kwargs):
#     """
#     Call this instead of subprocess.Popen to wrap stdout/stdin in
#     a logger.  Returns the same object.
#     """
#     kwargs = dict(kwargs)
#     kwargs['stdout'] = subprocess.PIPE
#     kwargs['stderr'] = subprocess.PIPE
#     s = subprocess.Popen(*args, **kwargs)
#     Thread(target=logger_run, args=(s, LOG, )).start()
#     return s

# def logger_run(subprocess, log):
#     """
#     Print warning to logger for all stdout.
#     """
#     stdout = subprocess.stdout
#     stderr = subprocess.stderr
#     while True:
#         try:
#             log.warn(stdout.next())
#         except StopIteration:
#             pass
#         try:
#             log.error(stderr.next())
#         except StopIteration:
#             pass

#         if not subprocess.poll():
#             time.sleep(.1)
#             continue
#         else:
#             break

#     log.warn('subprocess died')

class NoCardException(Exception):
    def __init__(self, card, card_ids):
        self.card = card
        Exception.__init__(self, 'Could not deal fake %s, tried %s' % (card, card_ids))

def fake_deal(r, mocked_key, card_name):
    """
    Fake the next spop to return the specified card (by name).  Throws
    an exception if there are no cards of that sort available in the
    collection when spop is hit.

    To queue several of these, you must do them in REVERSE order.  If
    you want 'tube' second and 'fire' first, then:

    fake_deal(r, 'game:deck', 'tube')
    fake_deal(r, 'game:deck', 'fire')
    """
    card_ids = [i for i in range(len(deck._DECK)) if deck._DECK[i].name == str(card_name)]
    orig_pop = r.spop

    def mock_pop(called_key):
        if mocked_key == called_key:
            r.spop = orig_pop
            for card_id in card_ids:
                if r.srem(mocked_key, card_id) == 1:
                    return str(card_id)
                raise NoCardException(card_name, card_ids)
        else:
            print "Warning: expecting to spop(%s), instead got spop(%s)" % (mocked_key, called_key)
            return orig_pop(called_key)

    r.spop = mock_pop


DB_NAME = 'TestServer'
HOST = "http://localhost:6767"

class TestOpengoldServer(unittest.TestCase):
    """
    Subclass this to get a test case that starts and shuts down both
    the Opengold server instance and mongrel. It will work with the
    "TestServer" Redis db, clearing it between tests.
    """

    @classmethod
    def setUpClass(cls):
        """
        Start up opengold & mongrel.
        """
        cls.server = subprocess.Popen('m2sh start -host localhost',
                                  shell=True,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE )
        cls.app = subprocess.Popen('python opengold/server.py %s' % DB_NAME,
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE )

        LOG.info("Waiting for server to start")
        time.sleep(2)
        LOG.info("Finished waiting for server to start")

    @classmethod
    def tearDownClass(cls):
        """
        Shut down opengold & mongrel.
        """
        cls.app.terminate()
        cls.app.wait()
        subprocess.Popen('m2sh stop -host localhost', shell=True)

    def setUp(self):
        """
        Clean DB entirely between tests.
        """
        redis.StrictRedis(db=DB_NAME).flushdb()
