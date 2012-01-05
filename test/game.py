"""
Test game.py
"""

from opengold.player import Player
from opengold.game import Game
from random import choice
import unittest


class TestGame(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_simulation(self):
        players = [Player('plato'),
                   Player('socrates'),
                   Player('aristotle')]

        game = Game(players)

        self.assertEquals(1, game.round_num)

        def loop():
            for player in players:
                result = game.submit(player, choice(['han', 'lando']))
                if result == True:
                    return False
            return True

        while(loop()):
            pass


# Primitive runner!
if __name__ == '__main__':
    unittest.main()
