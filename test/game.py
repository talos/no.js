"""
Test game.py
"""

import redis
import opengold.game as game
#from random import choice
import unittest
import time

class TestGame(unittest.TestCase):

    def setUp(self):
        self.r = redis.StrictRedis(db='TestGame')

    def tearDown(self):
        self.r.flushdb()

    def test_needs_multiple_players(self):
        game.join(self.r, 'game', 'hermit')
        self.assertFalse(game.confirm(self.r, 'game', 'hermit'))

    def test_move_before_start(self):
        game.join(self.r, 'game', 'foo')
        game.join(self.r, 'game', 'bar')
        self.assertFalse(game.move(self.r, 'game', 'foo', 'han'))

    def test_all_must_approve_start(self):
        game.join(self.r, 'game', 'alpha')
        game.join(self.r, 'game', 'beta')
        game.join(self.r, 'game', 'gaga')
        self.assertFalse(game.confirm(self.r, 'game', 'alpha'))
        self.assertFalse(game.confirm(self.r, 'game', 'beta'))
        self.assertEquals({'waiting': ['gaga'],
                           'undecided': ['alpha', 'beta'],
                           'decided': [],
                           'table': [],
                           'captured': [],
                           'pot': None,
                           'round': None,
                           'artifacts.destroyed': [],
                           'artifacts.seen.count': None,
                           'artifacts.in.play': []},
                          game.get_status(self.r, 'game'))

    def test_chat(self):
        game.join(self.r, 'game', 'betty')
        game.join(self.r, 'game', 'susie')
        game.join(self.r, 'game', 'martha')

        betty = game.subscription(self.r, 'game', 'betty')

        game.chat(self.r, 'game', 'rando', "what up gals")
        time.sleep(0.1)
        game.chat(self.r, 'game', 'betty', "who's that dude?")
        time.sleep(0.1)
        game.chat(self.r, 'game', 'martha', "no clue")
        time.sleep(0.1)

        chats = game.get_chats(self.r, 'game', 0)
        self.assertEquals(3, len(chats))
        self.assertEquals('rando', chats[0]['speaker'])
        self.assertEquals('what up gals', chats[0]['message'])
        self.assertEquals('betty', chats[1]['speaker'])
        self.assertEquals("who's that dude?", chats[1]['message'])
        self.assertEquals('martha', chats[2]['speaker'])
        self.assertEquals('no clue', chats[2]['message'])

        self.assertEquals('rando', betty.next()['chats'][0]['speaker'])
        self.assertEquals('betty', betty.next()['chats'][0]['speaker'])
        self.assertEquals('martha', betty.next()['chats'][0]['speaker'])

    # def test_starts(self):
    #     g = Game()
    #     g.add_player('george clinton')
    #     g.add_player('elmo')

    #     self.assertFalse(g.start('george clinton'))
    #     self.assertTrue(g.start('elmo'))

    #     george_msg = g.get_status('george clinton')
    #     # self.assertIsNotNone(george_msg)
    #     # self.assertIsNone(g.poll('george clinton'), msg="Should be no more messages")

    #     elmo_msg = g.get_status('elmo')
    #     # self.assertIsNotNone(elmo_msg)
    #     # self.assertIsNone(g.poll('elmo'), msg="Should be no more messages")

    #     self.assertEqual('george clinton', george_msg['you'])
    #     self.assertEqual('elmo', elmo_msg['you'])

    #     self.assertEqual(1, george_msg['round'])
    #     self.assertEqual(1, elmo_msg['round'])

    #     self.assertEqual(0, elmo_msg['pot'])
    #     self.assertEqual(0, george_msg['pot'])

    #     self.assertEqual(1, len(elmo_msg['artifacts']))
    #     self.assertEqual(1, len(george_msg['artifacts']))

    #     self.assertEqual(1, len(elmo_msg['table']))
    #     self.assertEqual(1, len(george_msg['table']))

    #     self.assertEqual([{'name': 'george clinton', 'move': 'undecided'},
    #                       {'name': 'elmo', 'move': 'undecided'}],
    #                      elmo_msg['players'])
    #     self.assertEqual([{'name': 'george clinton', 'move': 'undecided'},
    #                       {'name': 'elmo', 'move': 'undecided'}],
    #                      george_msg['players'])

    # def test_invalid_move(self):
    #     g = Game()
    #     g.add_player('foo')
    #     g.add_player('bar')
    #     g.start('foo')
    #     g.start('bar')
    #     self.assertFalse(g.submit('foo', 'blergh'))

    # def test_valid_move(self):
    #     g = Game()
    #     g.add_player('foo')
    #     g.add_player('bar')
    #     g.start('foo')
    #     g.start('bar')
    #     self.assertTrue(g.submit('bar', 'lando'))

    # def test_partial_completion(self):
    #     g = Game()
    #     g.add_player('socrates')
    #     g.add_player('aristotle')
    #     g.start('socrates')
    #     g.start('aristotle')
    #     g.submit('socrates', 'han')
    #     status = g.get_status()
    #     self.assertEquals(1, len(status.pop('table')))
    #     self.assertEquals(1, len(status.pop('artifacts')))
    #     self.assertIsNotNone(status.pop('pot'))

    #     self.assertEquals({
    #             'type'  : 'in_progress',
    #             'round' : 1,
    #             'players': [
    #                 {'name': 'socrates', 'move': 'decided'},
    #                 {'name': 'aristotle', 'move': 'undecided'}],
    #             'captured' : []
    #             }, status)

    # def test_one_deal(self):
    #     g = Game()
    #     g.add_player('socrates')
    #     g.add_player('aristotle')
    #     g.start('socrates')
    #     g.start('aristotle')
    #     g.submit('socrates', 'han')
    #     g.submit('aristotle', 'lando')
    #     status = g.get_status()

    #     # TODO this test doesn't correctly reflect artifact issues.
    #     self.assertEquals(3,
    #                       len(status.pop('table')) +
    #                       len(status.pop('captured')) +
    #                       len(status.pop('artifacts')))
    #     self.assertIsNotNone(status.pop('pot'))
    #     self.assertEquals({
    #             'type'  : 'in_progress',
    #             'round' : 1,
    #             'players': [
    #                 {'name': 'socrates', 'move': 'undecided'},
    #                 {'name': 'aristotle', 'move': 'lando'}]
    #             }, status)

    # def test_double_landos(self):
    #     g = Game()
    #     g.add_player('socrates')
    #     g.add_player('aristotle')
    #     g.start('socrates')
    #     g.start('aristotle')
    #     g.submit('socrates', 'lando')
    #     g.submit('aristotle', 'lando')

    #     status = g.get_status()

    #     self.assertEquals(1, len(status.pop('table')))
    #     self.assertTrue(len(status.pop('artifacts')) > 0)
    #     self.assertIsNotNone(status.pop('pot'))

    #     self.assertEquals({
    #             'type'  : 'in_progress',
    #             'round' : 2,
    #             'players': [
    #                 {'name': 'socrates', 'move': 'undecided'},
    #                 {'name': 'aristotle', 'move': 'undecided'}],
    #             'captured' : []
    #             }, status)

    # def test_double_hans(self):
    #     g = Game()
    #     g.add_player('socrates')
    #     g.add_player('aristotle')
    #     g.start('socrates')
    #     g.start('aristotle')

    #     while True:
    #         g.submit('socrates', 'han')
    #         g.submit('aristotle', 'han')
    #         if g.get_status()['round'] is 2:
    #             break

    #     # in case of double-hans, neither player gets loot
    #     self.assertEquals(0, g.get_status('socrates')['loot'])
    #     self.assertEquals(0, g.get_status('aristotle')['loot'])

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
