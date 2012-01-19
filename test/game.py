"""
Test game.py
"""

from opengold.player import Player
from opengold.game import Game
#from random import choice
import unittest


class TestGame(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_needs_players(self):
        g = Game('foo')
        self.assertFalse(g.start())

    def test_needs_multiple_players(self):
        g = Game('forest')
        g.add_player('hermit')
        self.assertFalse(g.start())

    def test_move_before_start(self):
        g = Game('duo')
        g.add_player('foo')
        g.add_player('bar')
        self.assertFalse(g.submit('foo', 'han'))

    def test_starts(self):
        g = Game('duo')
        g.add_player('foo')
        g.add_player('bar')
        self.assertTrue(g.start())

    def test_invalid_move(self):
        g = Game('duo')
        g.add_player('foo')
        g.add_player('bar')
        g.start()
        self.assertFalse(g.submit('foo', 'blergh'))

    def test_valid_move(self):
        g = Game('duo')
        g.add_player('foo')
        g.add_player('bar')
        g.start()
        self.assertTrue(g.submit('bar', 'lando'))

    # def test_simulation(self):
    #     players = [Player('plato'),
    #                Player('socrates'),
    #                Player('aristotle')]

    #     game = Game(players)

    #     self.assertEquals(1, game.round_num)

    #     def loop():
    #         for player in players:
    #             result = game.submit(player, choice(['han', 'lando']))
    #             if result == True:
    #                 return False
    #         return True

    #     while(loop()):
    #         pass


# Primitive runner!
if __name__ == '__main__':
    unittest.main()
