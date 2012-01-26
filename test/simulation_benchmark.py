"""
Simulate a lot of simultaneous games.
"""

import redis
import random
import time
from threading import Thread

from helpers import game, unittest, LOG

def random_ai():
    """
    An AI that randomly chooses between Han and Lando.
    """
    return random.choice(['han', 'lando'])

def run_player(r, k, name, ai, signal):
    """
    A self-contained player.  Joins game, then plays when it can.  If
    passed an ai, then will use it.
    """
    game.join(r, k, name)
    game.enter_temple(r, k, name)
    info = game.get_info(r, k, name, signal={})

    # This loop will not work if there is chat being simulated,
    # because then non-status bearing infos will be generated.
    while True:

        if info['status']['round'] == 0: # not yet started.
            pass
        elif(info['you']['location'] == 'temple'
             and 'decision' not in info['you']):
            game.move(r, k, name, random_ai())
        elif(info['you']['location'] == 'camp'
             and len(info['status']['table']) == 0): # could break on
            # artifact
            # capture
            game.enter_temple(r, k, name)
        elif info['status']['round'] == 5: # done!
            break
        else:
            raise Exception('Unhandled state: %s' % info)

        from pprint import pprint
        print pprint(info)

        # this blocks until something happens.
        info = game.get_info(r, k, name,
                             start_id=info['id'],
                             signal=signal)


class Player(object):
    def __init__(self, name, ai=random_ai):
        self.name = name
        self.ai = ai


class SimulationBenchmarkTest(unittest.TestCase):

    def setUp(self):
        self.r = redis.StrictRedis(db='SimulationBenchmark')
        self.r.flushdb()
        self.signal = {}
        self.timeout = 5

    def tearDown(self):
        self.signal['stop'] = True
        pass

    def simulate_game_threaded_players(self, game, *players):
        """
        Simulate a single game using a thread for each player.
        Returns a list of the started threads, which should be joined
        manually.
        """
        threads = [Thread(target=run_player,
                          args=(self.r, game, p.name, p.ai, self.signal))
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
