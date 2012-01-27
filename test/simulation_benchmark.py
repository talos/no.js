"""
Simulate a lot of simultaneous games.
"""

import redis
import random
import time
from threading import Thread

from helpers import game, unittest, LOG
from pprint import pprint

def random_ai():
    """
    An AI that randomly chooses between Han and Lando.
    """
    return random.choice(['han', 'lando'])

def run_player(r, k, name, ai):
    """
    A self-contained player.  Joins game, then plays when it can.  If
    passed an ai, then will use it.
    """
    game.join(r, k, name)
    informator = game.info(r, k, name)

    # This loop will not work if there is chat being simulated,
    # because then non-status bearing infos will be generated.
    for info in informator:
        print info
        if info is None:
            #print '%s Waiting for new info...' % name
            pass
        elif(info['you']['state'] == 'undecided'):
            game.move(r, k, name, random_ai())
        elif info['status']['round'] == 'done': # done!
            break
        else:
            pass

            #raise Exception('Unhandled state: %s' % pprint(info))

class Player(object):
    def __init__(self, name, ai=random_ai):
        self.name = name
        self.ai = ai


class SimulationBenchmarkTest(unittest.TestCase):

    def setUp(self):
        self.r = redis.StrictRedis(db='SimulationBenchmark')
        self.r.flushdb()
        self.timeout = 5

    def tearDown(self):
        pass

    def simulate_game_threaded_players(self, game, *players):
        """
        Simulate a single game using a thread for each player.
        Returns a list of the started threads, which should be joined
        manually.
        """
        threads = [Thread(target=run_player,
                          args=(self.r, game, p.name, p.ai))
                   for p in players]

        for thread in threads:
            thread.start()

        return threads

    def test_one_game_two_random_threaded_players(self):
        threads = self.simulate_game_threaded_players(
            'game',
            Player('betty', random_ai),
            Player('lou', random_ai))

        start = time.time()

        for thread in threads:
            thread.join(self.timeout)
            if thread.is_alive():
                self.fail('Thread did not die in %s seconds' % self.timeout)

        duration = time.time() - start

        print "test took %s seconds" % duration

# Primitive runner!
if __name__ == '__main__':
    unittest.main()
