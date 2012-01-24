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
        self.r.flushdb()

    def tearDown(self):
        #self.r.flushdb()
        pass

    def test_needs_multiple_players(self):
        self.assertTrue(game.join(self.r, 'game', 'hermit'))
        self.assertTrue(game.confirm(self.r, 'game', 'hermit'))
        info = game.get_info(self.r, 'game')
        self.assertTrue('status' in info)
        self.assertIsNone(game.get_info(self.r, 'game')['status']['round'])

    def test_move_before_start(self):
        self.assertTrue(game.join(self.r, 'game', 'foo'))
        self.assertTrue(game.join(self.r, 'game', 'bar'))
        self.assertFalse(game.move(self.r, 'game', 'foo', 'han'))

    def test_cannot_join_twice(self):
        self.assertTrue(game.join(self.r, 'game', 'dave'))
        self.assertTrue(game.join(self.r, 'game', 'john'))
        self.assertFalse(game.join(self.r, 'game', 'dave'))

    def test_all_must_approve_start(self):
        self.assertTrue(game.join(self.r, 'game', 'alpha'))
        self.assertTrue(game.join(self.r, 'game', 'beta'))
        self.assertTrue(game.join(self.r, 'game', 'gaga'))
        self.assertTrue(game.confirm(self.r, 'game', 'alpha'))
        self.assertTrue(game.confirm(self.r, 'game', 'beta'))

        info = game.get_info(self.r, 'game')
        self.assertFalse('chat' in info)
        self.assertFalse('you' in info)
        self.assertTrue('status' in info)
        self.assertTrue('update' in info)
        self.assertTrue('timestamp' in info)
        self.assertEquals(5, len(info['update']))

        self.assertEquals({'waiting': ['gaga'],
                           'confirmed': ['alpha', 'beta'],
                           'camp': [],
                           'moved': [],
                           'table': [],
                           'captured': [],
                           'pot': None,
                           'round': None,
                           'artifacts.destroyed': [],
                           'artifacts.seen.count': None,
                           'artifacts.in.play': []},
                          info['status'])

    def test_chat(self):
        self.assertTrue(game.join(self.r, 'game', 'betty'))
        self.assertTrue(game.join(self.r, 'game', 'susie'))
        self.assertTrue(game.join(self.r, 'game', 'martha'))

        self.assertTrue(game.chat(self.r, 'game', 'hero', "what up gals", True))
        time.sleep(0.1)
        self.assertFalse(game.chat(self.r, 'game', 'zero', "what up gals"))
        time.sleep(0.1)
        self.assertTrue(game.chat(self.r, 'game', 'betty', "who's that dude?"))
        time.sleep(0.1)
        self.assertTrue(game.chat(self.r, 'game', 'martha', "no clue"))
        time.sleep(0.1)

        info = game.get_info(self.r, 'game')
        self.assertTrue('chat' in info)
        self.assertTrue('status' in info)
        self.assertTrue('update' in info)
        self.assertTrue('timestamp' in info)

        chats = info['chat']
        self.assertEquals(3, len(chats))
        self.assertEquals('hero', chats[0]['speaker'])
        self.assertEquals('what up gals', chats[0]['message'])
        self.assertEquals('betty', chats[1]['speaker'])
        self.assertEquals("who's that dude?", chats[1]['message'])
        self.assertEquals('martha', chats[2]['speaker'])
        self.assertEquals('no clue', chats[2]['message'])

    def test_confirms_only_once(self):
        self.assertTrue(game.join(self.r, 'sesame street', 'george clinton'))
        self.assertTrue(game.join(self.r, 'sesame street', 'elmo'))

        self.assertTrue(game.confirm(self.r, 'sesame street', 'george clinton'))
        self.assertFalse(game.confirm(self.r, 'sesame street', 'george clinton'))

    def test_personal_info(self):
        self.assertTrue(game.join(self.r, 'sesame street', 'george clinton'))

        george_info = game.get_info(self.r, 'sesame street', 'george clinton')
        self.assertTrue('you' in george_info)
        you = george_info['you']
        self.assertEquals('george clinton', you['player'])
        self.assertEquals(0, you['loot'])
        self.assertEquals('waiting', you['moved'])
        self.assertEquals([], you['artifacts.captured'])

    def test_invalid_move(self):
        self.assertTrue(game.join(self.r, 'game', 'foo'))
        self.assertTrue(game.join(self.r, 'game', 'bar'))
        self.assertTrue(game.confirm(self.r, 'game', 'foo'))
        self.assertTrue(game.confirm(self.r, 'game', 'bar'))
        self.assertFalse(game.move(self.r, 'game', 'foo', 'blergh'))

    def test_valid_move(self):
        self.assertTrue(game.join(self.r, 'game', 'foo'))
        self.assertTrue(game.join(self.r, 'game', 'bar'))
        self.assertTrue(game.confirm(self.r, 'game', 'foo'))
        self.assertTrue(game.confirm(self.r, 'game', 'bar'))
        self.assertTrue(game.move(self.r, 'game', 'foo', 'lando'))

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
