"""
Simulate a lot of simultaneous games.
"""

import redis
import random
import time
import gevent

from uuid import uuid4
from threading import Thread

from helpers import game, unittest, LOG, COUNTRY_NAMES, PLAYER_NAMES
from pprint import pprint


def random_ai():
    """
    An AI that randomly chooses between Han and Lando.
    """
    return random.choice(['han', 'lando'])

def run_player(r, k, name, wait_for_n_players, sleeper,
               ai=random_ai, sleep_time=0):
    """
    A self-contained player.  Joins game, plays when it can.
    """

    game.join(r, k, name)

    for info in game.info(r, k, name):
        sleeper.sleep(sleep_time)

        player_state = info['you']['state']
        if player_state == 'joined':
            if len(info['state']['players']) == wait_for_n_players:
                game.start(r, k, name)
            else:
                pass
        elif player_state == 'undecided':
            game.move(r, k, name, ai())
        elif player_state in ['won', 'lost']: # done!
            return True

        sleeper.sleep(sleep_time)

class Player(object):
    def __init__(self, name, ai=random_ai):
        self.name = name
        self.ai = ai


class SimulationBenchmarkTest(unittest.TestCase):

    def setUp(self):
        self.r = redis.StrictRedis(db='SimulationBenchmark')
        self.r.flushdb()
        self.timeout = 240

    def tearDown(self):
        pass

    def simulate_game_gevent_players(self, game, *players):
        """
        Simulate a single game using gevent.  Returns an array of greenlets.
        """
        greenlets = [gevent.spawn(run_player,
                                  self.r, game, p.name, len(players), gevent, p.ai)
                     for p in players]
        return greenlets

    def x_games_x_greenlet_players(self, n_games, n_players):
        """
        Test a certain number of games w/ certain number of players,
        using greenlets.
        """
        greenlets = []

        for g in range(0, n_games):
            greenlets.extend(
                self.simulate_game_gevent_players(
                    str(uuid4()),
                    *[Player(str(uuid4()), random_ai) for p in range(0, n_players)]))

        start = time.time()

        gevent.joinall(greenlets, timeout=self.timeout)
        gevent.killall(greenlets)

        duration = time.time() - start

        if duration > self.timeout:
            self.fail('Greenlets not finished after %s seconds' % self.timeout)

        print "%s games with %s greenlet players took %s seconds." % \
            (n_games, n_players, duration)

    def simulate_game_threaded_players(self, game, *players):
        """
        Simulate a single game using a thread for each player.
        Returns a list of the started threads, which should be joined
        manually.
        """
        threads = [Thread(target=run_player,
                          args=(self.r, game, p.name, len(players), time, p.ai))
                   for p in players]

        for thread in threads:
            thread.start()

        return threads

    def x_games_x_threaded_players(self, n_games, n_players):
        """
        Test a certain number of games w/ certain number of players,
        using threading.
        """
        threads = []

        for g in range(0, n_games):
            threads.extend(
                self.simulate_game_threaded_players(
                    str(uuid4()),
                    *[Player(str(uuid4()), random_ai) for p in range(0, n_players)]))
#                    COUNTRY_NAMES.pop(),
#                    *[Player(PLAYER_NAMES.pop(), random_ai) for p in range(0, n_players)]))

        start = time.time()

        for thread in threads:
            thread.join(self.timeout)
            if thread.is_alive():
                self.fail('Thread did not die in %s seconds' % self.timeout)

        duration = time.time() - start

        print "%s games with %s threaded players took %s seconds." % \
            (n_games, n_players, duration)

    def test_one_game_two_random_greenlet_players(self):
        self.x_games_x_greenlet_players(1, 2)

    def test_one_game_eight_random_greenlet_players(self):
        self.x_games_x_greenlet_players(1, 8)

    def test_five_games_eight_random_greenlet_players(self):
        self.x_games_x_greenlet_players(5, 8)

    def test_fifty_games_four_random_greenlet_players(self):
        self.x_games_x_greenlet_players(50, 4)

    def test_hundred_games_four_random_greenlet_players(self):
        self.x_games_x_greenlet_players(100, 4)

    # def test_one_game_two_random_threaded_players(self):
    #     self.x_games_x_threaded_players(1, 2)

    # def test_one_game_three_random_threaded_players(self):
    #     self.x_games_x_threaded_players(1, 3)

    # def test_one_game_four_random_threaded_players(self):
    #     self.x_games_x_threaded_players(1, 4)

    # def test_one_game_six_random_threaded_players(self):
    #     self.x_games_x_threaded_players(1, 6)

    # def test_one_game_eight_random_threaded_players(self):
    #     self.x_games_x_threaded_players(1, 8)

    # def test_five_games_two_random_threaded_players(self):
    #     self.x_games_x_threaded_players(5, 2)

    # def test_five_games_three_random_threaded_players(self):
    #     self.x_games_x_threaded_players(5, 3)

    # def test_five_games_four_random_threaded_players(self):
    #     self.x_games_x_threaded_players(5, 4)

    # def test_five_games_six_random_threaded_players(self):
    #     self.x_games_x_threaded_players(5, 6)

    # def test_ten_games_two_random_threaded_players(self):
    #     self.x_games_x_threaded_players(10, 2)

    # def test_twentyfive_games_two_random_threaded_players(self):
    #     self.x_games_x_threaded_players(25, 2)

    # def test_fifty_games_two_random_threaded_players(self):
    #     self.x_games_x_threaded_players(50, 2)

    # def test_one_hundred_games_two_random_threaded_players(self):
    #     self.x_games_x_threaded_players(100, 2)

    # def test_one_hundred_games_four_random_threaded_players(self):
    #     self.x_games_x_threaded_players(100, 4)

# Primitive runner!
if __name__ == '__main__':
    unittest.main()
