"""
Test game.py
"""

import sys
if sys.version.find('2.7') == 0:
    import unittest
elif sys.version.find('2.6') == 0:
    import unittest2 as unittest
else:
    print "Python %s not tested with opengold.  Use 2.6 or 2.7." % sys.version
import time

import redis
import opengold.game as game
#from random import choice
from threading import Thread

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
        self.assertIn('status', info)
        self.assertEquals(0, game.get_info(self.r, 'game')['status']['round'])

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
        self.assertNotIn('chat', info)
        self.assertNotIn('you', info)
        self.assertIn('status', info)
        self.assertIn('update', info)
        self.assertIn('id', info)
        self.assertEquals(5, len(info['update']))
        self.assertEquals(5, info['id'])

        self.assertEquals({'waiting': ['gaga'],
                           'confirmed': ['alpha', 'beta'],
                           'camp': [],
                           'moved': [],
                           'table': [],
                           'captured': [],
                           'pot': 0,
                           'round': 0,
                           'artifacts.destroyed': [],
                           'artifacts.seen.count': 0,
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
        self.assertIn('id', info)
        self.assertIn('chat', info)
        self.assertIn('status', info)
        self.assertIn('update', info)

        chats = info['chat']
        self.assertEquals(3, len(chats))
        self.assertDictContainsSubset({'speaker': 'hero',
                                       'message': 'what up gals',
                                       'id': 4}, chats[0])
        self.assertDictContainsSubset({'speaker': 'betty',
                                       'message': "who's that dude?",
                                       'id': 5}, chats[1])
        self.assertDictContainsSubset({'speaker': 'martha',
                                       'message': 'no clue',
                                       'id': 6}, chats[2])

    def test_confirms_only_once(self):
        self.assertTrue(game.join(self.r, 'sesame street', 'george clinton'))
        self.assertTrue(game.join(self.r, 'sesame street', 'elmo'))

        self.assertTrue(game.confirm(self.r, 'sesame street', 'george clinton'))
        self.assertFalse(game.confirm(self.r, 'sesame street', 'george clinton'))

    def test_personal_info(self):
        self.assertTrue(game.join(self.r, 'sesame street', 'george clinton'))

        george_info = game.get_info(self.r, 'sesame street', 'george clinton')
        self.assertIn('you', george_info)
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
        time.sleep(0.01)
        self.assertTrue(game.join(self.r, 'game', 'bar'))
        time.sleep(0.01)
        self.assertTrue(game.confirm(self.r, 'game', 'foo'))
        time.sleep(0.01)
        self.assertTrue(game.confirm(self.r, 'game', 'bar'))
        time.sleep(0.01)
        self.assertTrue(game.move(self.r, 'game', 'foo', 'lando'))

        info = game.get_info(self.r, 'game')
        self.assertIn('status', info)
        self.assertIn('id', info)
        self.assertIn(info['id'], [8, 9])
        self.assertNotIn('you', info)

        status = info['status']
        self.assertEquals(1, len(status.pop('table')))
        self.assertEquals(1, len(status.pop('artifacts.in.play')))
        self.assertLessEqual(status.pop('artifacts.seen.count'), 1)
        self.assertEquals({
                'waiting': [],
                'confirmed': ['bar'],
                'camp': [],
                'moved': ['foo'],
                'pot': 0,
                'round': 1,
                'captured': [],
                'artifacts.destroyed': [] }, status)

        self.assertIn('update', info)
        updates = info['update']
        self.assertIn(len(updates), [8, 9]) # Extra notification if card was artifact
        self.assertDictContainsSubset({'joined': 'foo',
                                       'id': 1 }, updates[0])
        self.assertDictContainsSubset({'joined': 'bar',
                                       'id': 2 }, updates[1])
        self.assertDictContainsSubset({'confirmed': 'foo',
                                       'id': 3 }, updates[2])
        self.assertDictContainsSubset({'confirmed': 'bar',
                                       'id': 4 }, updates[3])
        self.assertDictContainsSubset({'round': 1,
                                       'id': 5 }, updates[4])
        self.assertEquals(6, updates[5]['id'])
        self.assertIn('artifacts.in.play', updates[5])
        self.assertIsInstance(updates[5]['artifacts.in.play'], str)
        self.assertEquals(7, updates[6]['id'])
        self.assertIn('card', updates[6])
        self.assertIsInstance(updates[6]['card'], str)
        # Extra notification if the card happened to have been an artifact
        if len(updates) == 9:
            self.assertDictContainsSubset({'artifacts.seen.count': 1,
                                           'id': 8}, updates[7])
        self.assertDictContainsSubset({'moved': 'foo'}, updates.pop())

        foo = game.get_info(self.r, 'game', 'foo')
        self.assertIn('you', foo)
        self.assertEquals({
                'player': 'foo',
                'moved': 'lando',
                'loot' : 0,
                'artifacts.captured': [] }, foo['you'])

        bar = game.get_info(self.r, 'game', 'bar')
        self.assertIn('you', bar)

        self.assertEquals({
                'player': 'bar',
                'moved': 'confirmed',
                'loot': 0,
                'artifacts.captured': [] }, bar['you'])

    def test_blocking_info(self):
        t = Thread(target=game.get_info, args=[self.r, 'game'])
        self.assertTrue(t.is_alive())
        time.sleep(0.5)
        self.assertTrue(t.is_alive())
        self.assertTrue(game.join(self.r, 'game', 'some dude'))
        self.assertFalse(t.is_alive())

    def test_blocking_info_via_id(self):
        self.assertTrue(game.join(self.r, 'game', 'thing one'))
        t_all_info = Thread(target=game.get_info, args=(self.r, 'game',))
        self.assertFalse(t_all_info.is_alive())

        info = game.get_info(self.r, 'game')
        self.assertIn('id', info)
        last_id = info['id']

        t_partial_info = Thread(target=game.get_info,
                                args=(self.r, 'game',),
                                kwargs={'start_id': last_id+1})
        self.assertTrue(t_partial_info.is_alive())
        time.sleep(0.5)
        self.assertTrue(t_partial_info.is_alive())
        self.assertTrue(game.join(self.r, 'game', 'some dude'))
        self.assertFalse(t_partial_info.is_alive())

    # def test_full_deal(self):
    #     self.assertTrue(game.join(self.r, 'game', 'socrates'))
    #     self.assertTrue(game.join(self.r, 'game', 'aristotle'))
    #     self.assertTrue(game.confirm(self.r, 'game', 'aristotle'))
    #     self.assertTrue(game.confirm(self.r, 'game', 'socrates'))
    #     self.assertTrue(game.move(self.r, 'game', 'foo', 'lando'))
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
