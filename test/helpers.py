import subprocess
import redis
import time
import unittest
from opengold.deck import _DECK

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
    card_ids = [i for i in range(len(_DECK)) if _DECK[i].name == str(card_name)]
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
        cls.server = subprocess.Popen('m2sh start -host localhost', shell=True)
        cls.app = subprocess.Popen('python opengold/server.py %s' % DB_NAME, shell=True)
        print "Waiting for server to start"
        time.sleep(2)
        print "Finished waiting for server to start"

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
