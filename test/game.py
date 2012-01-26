"""
Test game.py
"""

import time

import redis
from helpers import fake_deal, game, unittest

#from random import choice
from threading import Thread


class TestGame(unittest.TestCase):

    def setUp(self):
        self.r = redis.StrictRedis(db='TestGame')
        self.r.flushdb()

    def tearDown(self):
        #self.r.flushdb()
        pass

    def test_multiple_game_names(self):
        game.join(self.r, 'the hills', 'foo')
        game.join(self.r, 'the valleys', 'bar')

        self.assertEquals(['the hills', 'the valleys'],
                          game.list_names(self.r))

    def test_needs_multiple_players(self):
        self.assertTrue(game.join(self.r, 'game', 'hermit'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'hermit'))
        info = game.info(self.r, 'game').next()
        self.assertIn('status', info)
        self.assertEquals(0, game.info(self.r, 'game').next()['status']['round'])

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
        self.assertTrue(game.enter_temple(self.r, 'game', 'alpha'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'beta'))

        info = game.info(self.r, 'game').next()
        self.assertNotIn('chat', info)
        self.assertNotIn('you', info)
        self.assertIn('status', info)
        self.assertIn('update', info)
        self.assertIn('id', info)
        self.assertEquals(5, len(info['update']))
        self.assertEquals(5, info['id'])

        updates = info['update']
        self.assertDictContainsSubset({'camp': 'alpha', 'id': 1}, updates[0])
        self.assertDictContainsSubset({'camp': 'beta', 'id': 2}, updates[1])
        self.assertDictContainsSubset({'camp': 'gaga', 'id': 3}, updates[2])
        self.assertDictContainsSubset({'temple': 'alpha', 'id': 4}, updates[3])
        self.assertDictContainsSubset({'temple': 'beta', 'id': 5}, updates[4])

        self.assertEquals({'players': [{'name' : 'alpha',
                                        'decision': False,
                                        'location': 'temple'},
                                       {'name': 'beta',
                                        'decision': False,
                                        'location': 'temple'},
                                       {'name': 'gaga',
                                        'decision': False,
                                        'location': 'camp'}],
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

        info = game.info(self.r, 'game').next()
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

        self.assertTrue(game.enter_temple(self.r, 'sesame street', 'george clinton'))
        self.assertFalse(game.enter_temple(self.r, 'sesame street', 'george clinton'))

    def test_personal_info(self):
        self.assertTrue(game.join(self.r, 'sesame street', 'george clinton'))

        george_info = game.info(self.r, 'sesame street', 'george clinton').next()
        self.assertIn('you', george_info)
        self.assertDictContainsSubset({'name': 'george clinton',
                                       'artifacts.captured': [],
                                       'loot': 0,
                                       'location': 'camp'}, george_info['you'])

    def test_invalid_move(self):
        self.assertTrue(game.join(self.r, 'game', 'foo'))
        self.assertTrue(game.join(self.r, 'game', 'bar'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'foo'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'bar'))
        self.assertFalse(game.move(self.r, 'game', 'foo', 'blergh'))

    def test_double_move_prohibited(self):
        self.assertTrue(game.join(self.r, 'game', 'foo'))
        self.assertTrue(game.join(self.r, 'game', 'bar'))
        self.assertTrue(game.join(self.r, 'game', 'baz'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'foo'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'baz'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'bar'))
        self.assertTrue(game.move(self.r, 'game', 'bar', 'lando'))
        self.assertTrue(game.move(self.r, 'game', 'foo', 'han'))
        self.assertFalse(game.move(self.r, 'game', 'bar', 'han'))

    def test_cannot_enter_after_move(self):
        self.assertTrue(game.join(self.r, 'game', 'foo'))
        self.assertTrue(game.join(self.r, 'game', 'bar'))
        self.assertTrue(game.join(self.r, 'game', 'baz'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'foo'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'baz'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'bar'))
        self.assertTrue(game.move(self.r, 'game', 'bar', 'lando'))
        self.assertTrue(game.move(self.r, 'game', 'foo', 'han'))
        self.assertFalse(game.enter_temple(self.r, 'game', 'bar'))

    def test_valid_move(self):
        self.assertTrue(game.join(self.r, 'game', 'foo'))
        time.sleep(0.01)
        self.assertTrue(game.join(self.r, 'game', 'bar'))
        time.sleep(0.01)
        self.assertTrue(game.enter_temple(self.r, 'game', 'foo'))
        time.sleep(0.01)
        self.assertTrue(game.enter_temple(self.r, 'game', 'bar'))
        time.sleep(0.01)
        self.assertTrue(game.move(self.r, 'game', 'foo', 'lando'))

        info = game.info(self.r, 'game').next()
        self.assertIn('status', info)
        self.assertIn('id', info)
        self.assertIn(info['id'], [8, 9])
        self.assertNotIn('you', info)

        status = info['status']
        self.assertEquals(1, len(status.pop('table')))
        self.assertEquals(1, len(status.pop('artifacts.in.play')))
        self.assertLessEqual(status.pop('artifacts.seen.count'), 1)
        self.assertEquals({
                'players': [{'name':'bar',
                             'location': 'temple',
                             'decision': False},
                            {'name':'foo',
                             'location': 'temple',
                             'decision': True}],
                'pot': 0,
                'round': 1,
                'captured': [],
                'artifacts.destroyed': [] }, status)

        self.assertIn('update', info)
        updates = info['update']
        self.assertIn(len(updates), [8, 9]) # Extra notification if card was artifact
        self.assertDictContainsSubset({'camp': 'foo', 'id': 1 }, updates[0])
        self.assertDictContainsSubset({'camp': 'bar', 'id': 2 }, updates[1])
        self.assertDictContainsSubset({'temple': 'foo', 'id': 3 }, updates[2])
        self.assertDictContainsSubset({'temple': 'bar', 'id': 4 }, updates[3])
        self.assertDictContainsSubset({'round': 1, 'id': 5 }, updates[4])
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
        self.assertDictContainsSubset({'decision': 'foo'}, updates.pop())

        foo = game.info(self.r, 'game', 'foo').next()
        self.assertIn('you', foo)
        self.assertEquals({
                'name': 'foo',
                'location': 'temple',
                'loot': 0,
                'artifacts.captured': [],
                'decision': 'lando' }, foo['you'])

        bar = game.info(self.r, 'game', 'bar').next()
        self.assertIn('you', bar)

        self.assertEquals({
                'name': 'bar',
                'loot': 0,
                'artifacts.captured': [],
                'location': 'temple' }, bar['you'])

    def test_blocking_info(self):
        info = game.info(self.r, 'blocked')
        self.assertIsNone(info.next()) # put it into blocking mode
        t = Thread(target=info.next)
        t.start()
        self.assertTrue(t.is_alive())
        time.sleep(0.5)

        self.assertTrue(t.is_alive())

        self.assertTrue(game.join(self.r, 'blocked', 'some dude'))
        t.join(1)
        self.assertFalse(t.is_alive())

    def test_blocking_info_via_id(self):
        info = game.info(self.r, 'game')
        self.assertTrue(game.join(self.r, 'game', 'thing one'))
        t_all_info = Thread(target=info.next)
        t_all_info.start()
        t_all_info.join(1)
        self.assertFalse(t_all_info.is_alive())

        self.assertIsNone(info.next()) # put it into blocking mode
        t_partial_info = Thread(target=info.next)

        t_partial_info.start()
        self.assertTrue(t_partial_info.is_alive())
        time.sleep(0.5)
        self.assertTrue(t_partial_info.is_alive())

        self.assertTrue(game.join(self.r, 'game', 'some dude'))
        t_partial_info.join(1)
        self.assertFalse(t_partial_info.is_alive())

    def test_triple_landos_moves_back_to_waiting(self):
        self.assertTrue(game.join(self.r, 'game', 'socrates'))
        self.assertTrue(game.join(self.r, 'game', 'aristotle'))
        self.assertTrue(game.join(self.r, 'game', 'plato'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'socrates'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'aristotle'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'plato'))
        self.assertTrue(game.move(self.r, 'game', 'socrates', 'lando'))
        self.assertTrue(game.move(self.r, 'game', 'aristotle', 'lando'))
        self.assertTrue(game.move(self.r, 'game', 'plato', 'lando'))

        info = game.info(self.r, 'game').next()
        self.assertIn('status', info)
        self.assertDictContainsSubset({
                'round': 1,
                'players': [{'name':'aristotle',
                             'location': 'camp',
                             'decision': False},
                            {'name':'plato',
                             'location': 'camp',
                             'decision': False},
                            {'name':'socrates',
                             'location': 'camp',
                             'decision': False}]}, info['status'])

    def test_artifact_destruction(self):
        fake_deal(self.r, 'game:deck', 'tube')
        fake_deal(self.r, 'game:artifacts.unseen', 'tube')

        self.assertTrue(game.join(self.r, 'game', 'socrates'))
        self.assertTrue(game.join(self.r, 'game', 'aristotle'))

        self.assertTrue(game.enter_temple(self.r, 'game', 'socrates'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'aristotle'))
        self.assertTrue(game.move(self.r, 'game', 'socrates', 'lando'))
        self.assertTrue(game.move(self.r, 'game', 'aristotle', 'lando'))

        info = game.info(self.r, 'game').next()
        self.assertDictContainsSubset({'camp': 'socrates', 'id': 1}, info['update'][0])
        self.assertDictContainsSubset({'camp': 'aristotle', 'id': 2}, info['update'][1])
        self.assertDictContainsSubset({'temple': 'socrates', 'id': 3}, info['update'][2])
        self.assertDictContainsSubset({'temple': 'aristotle', 'id': 4}, info['update'][3])
        self.assertDictContainsSubset({'round': 1, 'id': 5}, info['update'][4])
        self.assertDictContainsSubset({'artifacts.in.play': 'tube', 'id': 6}, info['update'][5])
        self.assertDictContainsSubset({'card': 'tube', 'id': 7}, info['update'][6])
        self.assertDictContainsSubset({'artifacts.seen.count': 1, 'id': 8}, info['update'][7])
        self.assertDictContainsSubset({'decision': 'socrates', 'id': 9}, info['update'][8])
        self.assertDictContainsSubset({'decision': 'aristotle', 'id': 10}, info['update'][9])
        self.assertDictContainsSubset({'artifacts.destroyed':
                                           {'players': ['aristotle', 'socrates'],
                                            'card': 'tube',
                                            'value': 5},
                                       'id': 11 }, info['update'][10])
        self.assertDictContainsSubset({'captured':
                                           {'players': ['aristotle', 'socrates'],
                                            'value': 0,
                                            'pot': 0 },
                                       'id': 12}, info['update'][11])

        self.assertDictContainsSubset({
                'pot': 0,
                'captured': [],
                'artifacts.in.play': [],
                'artifacts.seen.count': 1,
                'artifacts.destroyed': ['tube'] }, info['status'])

        self.assertEquals({'name': 'aristotle',
                           'loot': 0,
                           'artifacts.captured': [],
                           'location': 'camp'},
                          game.info(self.r, 'game', 'aristotle').next()['you'])

        self.assertEquals({'name': 'socrates',
                           'loot': 0,
                           'artifacts.captured': [],
                           'location': 'camp'},
                          game.info(self.r, 'game', 'socrates').next()['you'])

    def test_artifact_capture(self):
        self.assertTrue(game.join(self.r, 'game', 'socrates'))
        self.assertTrue(game.join(self.r, 'game', 'aristotle'))

        fake_deal(self.r, 'game:deck', 'tube')
        fake_deal(self.r, 'game:artifacts.unseen', 'tube')

        self.assertTrue(game.enter_temple(self.r, 'game', 'socrates'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'aristotle'))
        self.assertTrue(game.move(self.r, 'game', 'socrates', 'han'))
        self.assertTrue(game.move(self.r, 'game', 'aristotle', 'lando'))

        info = game.info(self.r, 'game').next()

        self.assertDictContainsSubset({'camp': 'socrates', 'id': 1}, info['update'][0])
        self.assertDictContainsSubset({'camp': 'aristotle', 'id': 2}, info['update'][1])
        self.assertDictContainsSubset({'temple': 'socrates', 'id': 3}, info['update'][2])
        self.assertDictContainsSubset({'temple': 'aristotle', 'id': 4}, info['update'][3])
        self.assertDictContainsSubset({'round': 1, 'id': 5}, info['update'][4])
        self.assertDictContainsSubset({'artifacts.in.play': 'tube', 'id': 6}, info['update'][5])
        self.assertDictContainsSubset({'card': 'tube', 'id': 7}, info['update'][6])
        self.assertDictContainsSubset({'artifacts.seen.count': 1, 'id': 8}, info['update'][7])
        self.assertDictContainsSubset({'decision': 'socrates', 'id': 9}, info['update'][8])
        self.assertDictContainsSubset({'decision': 'aristotle', 'id': 10}, info['update'][9])
        self.assertDictContainsSubset({'artifacts.captured':
                                           {'players': 'aristotle',
                                            'card': 'tube',
                                            'value': 5},
                                       'id': 11 }, info['update'][10])
        self.assertDictContainsSubset({'captured':
                                           {'players': ['aristotle'],
                                            'value': 5,
                                            'pot': 0 },
                                       'id': 12}, info['update'][11])

        self.assertDictContainsSubset({
                'pot': 0,
                'captured': [],
                'artifacts.in.play': [],
                'artifacts.seen.count': 1,
                'artifacts.destroyed': [] }, info['status'])

        self.assertEquals({'name': 'aristotle',
                           'loot': 5,
                           'artifacts.captured': ['tube'],
                           'location': 'camp'},
                          game.info(self.r, 'game', 'aristotle').next()['you'])

        self.assertEquals({'name': 'socrates',
                           'loot': 0,
                           'artifacts.captured': [],
                           'location': 'temple'},
                          game.info(self.r, 'game', 'socrates').next()['you'])

    def test_second_round(self):
        self.assertTrue(game.join(self.r, 'game', 'socrates'))
        self.assertTrue(game.join(self.r, 'game', 'aristotle'))
        self.assertTrue(game.join(self.r, 'game', 'plato'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'socrates'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'aristotle'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'plato'))
        self.assertTrue(game.move(self.r, 'game', 'socrates', 'lando'))
        self.assertTrue(game.move(self.r, 'game', 'aristotle', 'lando'))
        self.assertTrue(game.move(self.r, 'game', 'plato', 'lando'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'socrates'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'aristotle'))
        self.assertTrue(game.enter_temple(self.r, 'game', 'plato'))

        info = game.info(self.r, 'game').next()
        self.assertIn('status', info)
        self.assertEquals(1, len(info['status']['table']))
        self.assertDictContainsSubset({
                'round': 2,
                'players': [{'name':'aristotle',
                             'location': 'temple',
                             'decision': False},
                            {'name':'plato',
                             'location': 'temple',
                             'decision': False},
                            {'name':'socrates',
                             'location': 'temple',
                             'decision': False}]}, info['status'])

    def test_full_game(self):
        self.assertTrue(game.join(self.r, 'game', 'socrates'))
        self.assertTrue(game.join(self.r, 'game', 'aristotle'))

        self.assertTrue(game.chat(self.r, 'game', 'aristotle', 'what up soc'))

        info = game.info(self.r, 'game').next()
        self.assertEquals(3, info['id'])
        self.assertEquals(2, len(info['update']))
        self.assertDictContainsSubset({'camp': 'socrates', 'id': 1}, info['update'][0])
        self.assertDictContainsSubset({'camp': 'aristotle', 'id': 2}, info['update'][1])
        self.assertEquals(1, len(info['chat']))
        self.assertDictContainsSubset({'speaker': 'aristotle',
                                       'message': 'what up soc',
                                       'id': 3}, info['chat'][0])
        self.assertEquals({
                'players': [{'name': 'aristotle',
                             'location': 'camp',
                             'decision': False},
                            {'name': 'socrates',
                             'location': 'camp',
                             'decision': False}],
                'pot': 0,
                'round': 0,
                'table': [],
                'captured': [],
                'artifacts.in.play': [],
                'artifacts.seen.count': 0,
                'artifacts.destroyed': [] }, info['status'])

        # self.assertFalse(game.move(self.r, 'game', 'aristotle', 'han'))
        # self.assertTrue(game.enter_temple(self.r, 'game', 'aristotle'))

        # self.assertEquals({
        #         'players': [{'name': 'aristotle',
        #                      'location': 'camp',
        #                      'decision': False},
        #                     {'name': 'plato',
        #                      'location': 'camp',
        #                      'decision': False},
        #                     {'name': 'socrates',
        #                      'location': 'camp',
        #                      'decision': False},

        # self.assertTrue(game.join(self.r, 'game', 'plato'))

        # self.assertEquals({
        #         'players': [{'name': 'aristotle',
        #                      'location': 'camp',
        #                      'decision': False},
        #                     {'name': 'plato',
        #                      'location': 'camp',
        #                      'decision': False},
        #                     {'name': 'socrates',
        #                      'location': 'camp',
        #                      'decision': False},
        #         }, game.get_info(self.r, 'game'))

        # fake_deal(self.r, 'game:artifacts.unseen', 'tube')
        # fake_deal(self.r, 'game:deck', 'bitches')

        # self.assertTrue(game.enter_temple(self.r, 'game', 'socrates'))
        # self.assertTrue(game.enter_temple(self.r, 'game', 'aristotle'))
        # self.assertTrue(game.enter_temple(self.r, 'game', 'plato'))

# Primitive runner!
if __name__ == '__main__':
    unittest.main()
