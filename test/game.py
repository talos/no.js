"""
Test game.py
"""

import time

import redis
from helpers import fake_deal, game, unittest

from threading import Thread


class TestGame(unittest.TestCase):

    def setUp(self):
        self.r = redis.StrictRedis(db='TestGame')
        self.r.flushdb()

    def tearDown(self):
        #self.r.flushdb()
        pass

    def test_join(self):
        self.assertTrue(game.join(self.r, 'game', 'dave'))
        info = game.info(self.r, 'game', 'dave').next()
        self.assertDictContainsSubset({
                'state': 'joined',
                'name': 'dave' }, info['you'])
        self.assertEquals([{'name': 'dave', 'state': 'joined' }],
                          info['state']['players'])

    def test_cannot_join_twice(self):
        game.join(self.r, 'game', 'dave')
        self.assertFalse(game.join(self.r, 'game', 'dave'))
        info = game.info(self.r, 'game', 'dave').next()
        self.assertEquals(1, len(info['state']['players']))

    def test_start_statuses(self):
        game.join(self.r, 'game', 'dave')
        self.assertTrue(game.start(self.r, 'game', 'dave'))
        info = game.info(self.r, 'game', 'dave').next()
        self.assertDictContainsSubset({
                'state': 'camp',
                'name': 'dave' }, info['you'])
        self.assertEquals([{'name': 'dave', 'state': 'camp' }],
                          info['state']['players'])

    def test_needs_multiple_players_to_start(self):
        game.join(self.r, 'game', 'hermit')
        game.start(self.r, 'game', 'hermit')
        info = game.info(self.r, 'game').next()
        self.assertNotIn('round', info['state'])

    def test_single_player_starting_gets_more_players_update(self):
        game.join(self.r, 'game', 'hermit')
        game.start(self.r, 'game', 'hermit')
        info = game.info(self.r, 'game').next()

        self.assertDictContainsSubset({'more_players': True}, info['updates'].pop(0))

    def test_all_must_approve_start(self):
        game.join(self.r, 'game', 'alpha')
        game.join(self.r, 'game', 'beta')
        game.join(self.r, 'game', 'gaga')
        game.start(self.r, 'game', 'alpha')
        game.start(self.r, 'game', 'beta')

        info = game.info(self.r, 'game').next()
        self.assertNotIn('round', info['state'])

    def test_start_game(self):
        game.join(self.r, 'game', 'alpha')
        game.join(self.r, 'game', 'beta')
        game.start(self.r, 'game', 'alpha')

        game.start(self.r, 'game', 'beta')

        info = game.info(self.r, 'game').next()
        self.assertEquals('1', info['state']['round'])
        self.assertEquals([{ 'name': 'alpha',
                             'state': 'undecided'},
                           { 'name': 'beta',
                             'state': 'undecided'}], info['state']['players'])

    def test_updates_most_recent_first(self):
        """
        The first update should be the most recent, then they work backwards.
        """
        game.join(self.r, 'game', 'first')
        game.join(self.r, 'game', 'second')
        game.join(self.r, 'game', 'third')

        info = game.info(self.r, 'game').next()

        self.assertDictContainsSubset({'join': 'third'}, info['updates'].pop(0))
        self.assertDictContainsSubset({'join': 'second'}, info['updates'].pop(0))
        self.assertDictContainsSubset({'join': 'first'}, info['updates'].pop(0))

    def test_chat(self):
        game.join(self.r, 'game', 'loner')
        self.assertTrue(game.chat(self.r, 'game', 'loner', 'just me myself and i'))
        info = game.info(self.r, 'game').next()
        self.assertDictContainsSubset({'chat': {
                    'speaker': 'loner',
                    'message': 'just me myself and i'}}, info['updates'].pop(0))

    def test_superuser_chat(self):
        game.join(self.r, 'game', 'betty')
        game.join(self.r, 'game', 'susie')
        game.join(self.r, 'game', 'martha')

        self.assertTrue(game.chat(self.r, 'game', 'hero', "what up gals", True))
        self.assertFalse(game.chat(self.r, 'game', 'zero', "me too!"))
        game.chat(self.r, 'game', 'betty', "who's that dude?")
        game.chat(self.r, 'game', 'martha', "no clue")

        info = game.info(self.r, 'game').next()

        self.assertEquals({ 'speaker': 'martha',
                            'message': 'no clue'},
                          info['updates'].pop(0)['chat'])
        self.assertEquals({ 'speaker': 'betty',
                            'message': "who's that dude?"},
                          info['updates'].pop(0)['chat'])
        self.assertEquals({ 'speaker': 'hero',
                            'message': 'what up gals'},
                          info['updates'].pop(0)['chat'])

    def test_no_move_without_start(self):
        game.join(self.r, 'game', 'max')
        game.join(self.r, 'game', 'jenny')
        game.start(self.r, 'game', 'jenny')
        self.assertFalse(game.move(self.r, 'game', 'jenny', 'han'))
        info = game.info(self.r, 'game', 'jenny').next()
        self.assertEquals('camp', info['you']['state'])

    def test_move(self):
        game.join(self.r, 'game', 'max')
        game.join(self.r, 'game', 'jenny')
        game.start(self.r, 'game', 'max')
        game.start(self.r, 'game', 'jenny')
        self.assertTrue(game.move(self.r, 'game', 'jenny', 'han'))
        info = game.info(self.r, 'game', 'jenny').next()
        self.assertEquals([{ 'name': 'jenny',
                             'state': 'moved'},
                           { 'name': 'max',
                             'state': 'undecided'}], info['state']['players'])
        self.assertEquals('han', info['you']['state'])

    # def test_invalid_move(self):
    #     self.assertTrue(game.join(self.r, 'game', 'foo'))
    #     self.assertTrue(game.join(self.r, 'game', 'bar'))
    #     self.assertFalse(game.move(self.r, 'game', 'foo', 'blergh'))

    # def test_double_move_prohibited(self):
    #     self.assertTrue(game.join(self.r, 'game', 'foo'))
    #     self.assertTrue(game.join(self.r, 'game', 'bar'))
    #     self.assertTrue(game.join(self.r, 'game', 'baz'))
    #     self.assertTrue(game.move(self.r, 'game', 'bar', 'lando'))
    #     self.assertTrue(game.move(self.r, 'game', 'foo', 'han'))
    #     self.assertFalse(game.move(self.r, 'game', 'bar', 'han'))

    # def test_cannot_join_after_move(self):
    #     self.assertTrue(game.join(self.r, 'game', 'foo'))
    #     self.assertTrue(game.join(self.r, 'game', 'bar'))
    #     self.assertTrue(game.join(self.r, 'game', 'baz'))
    #     self.assertTrue(game.move(self.r, 'game', 'bar', 'lando'))
    #     self.assertTrue(game.move(self.r, 'game', 'foo', 'han'))
    #     self.assertFalse(game.join(self.r, 'game', 'bar'))

    # def test_valid_move(self):
    #     self.assertTrue(game.join(self.r, 'game', 'foo'))
    #     time.sleep(0.01)
    #     self.assertTrue(game.join(self.r, 'game', 'bar'))
    #     time.sleep(0.01)
    #     self.assertTrue(game.move(self.r, 'game', 'foo', 'lando'))

    #     info = game.info(self.r, 'game').next()
    #     self.assertIn('status', info)
    #     self.assertIn('id', info)
    #     self.assertIn(info['id'], [8, 9])
    #     self.assertNotIn('you', info)

    #     status = info['status']
    #     self.assertEquals(1, len(status.pop('table')))
    #     self.assertEquals(1, len(status.pop('artifacts.in.play')))
    #     self.assertLessEqual(status.pop('artifacts.seen.count'), 1)
    #     self.assertEquals({
    #             'players': [{'name':'bar',
    #                          'state': 'undecided'},
    #                         {'name': 'foo',
    #                          'state': 'moved'}],
    #             'pot': 0,
    #             'round': None,
    #             'captured': [],
    #             'artifacts.destroyed': [] }, status)

    #     self.assertIn('update', info)
    #     updates = info['update']
    #     self.assertIn(len(updates), [8, 9]) # Extra notification if card was artifact
    #     self.assertDictContainsSubset({'camp': 'foo', 'id': 1 }, updates[0])
    #     self.assertDictContainsSubset({'camp': 'bar', 'id': 2 }, updates[1])
    #     self.assertDictContainsSubset({'moved': 'foo', 'id': 3 }, updates[2])

    #     foo = game.info(self.r, 'game', 'foo').next()
    #     self.assertIn('you', foo)
    #     self.assertEquals({
    #             'name': 'foo',
    #             'state': 'lando',
    #             'loot': 0,
    #             'artifacts.captured': [] }, foo['you'])

    #     bar = game.info(self.r, 'game', 'bar').next()
    #     self.assertIn('you', bar)

    #     self.assertEquals({
    #             'name': 'bar',
    #             'loot': 0,
    #             'artifacts.captured': [],
    #             'state': 'undecided' }, bar['you'])

    def test_no_games(self):
        """
        .games() should initially return an empty array if there were no games.
        """
        games = game.games(self.r)
        self.assertEquals([], games.next()['games'])

    def test_no_games_zero_id(self):
        """
        .games() should initially return an empty array if there were no games.
        """
        games = game.games(self.r)
        self.assertEquals(0, games.next()['id'])

    def test_games_advances(self):
        """
        .games() should return a generator that only advances when a
        new game is made.
        """
        games = game.games(self.r)
        games.next()  # pull out the empty array

        t = Thread(target=games.next)
        t.start()

        self.assertTrue(t.is_alive())
        time.sleep(0.5)
        self.assertTrue(t.is_alive())

        game.join(self.r, 'unblocked', 'some dude') # create a game

        t.join(1)
        self.assertFalse(t.is_alive())

    def test_games_waits_for_id(self):
        """
        The ID passed to games should cause it to hold on a response
        until there are more than that number of games.
        """
        games = game.games(self.r, 3)

        t = Thread(target=games.next)
        t.start()

        game.join(self.r, 'one', 'player')
        game.join(self.r, 'two', 'player')
        game.join(self.r, 'three', 'player')
        self.assertTrue(t.is_alive())
        game.join(self.r, 'four', 'player')

        t.join(1)
        self.assertFalse(t.is_alive())

    def test_games_names(self):
        game.join(self.r, 'the hills', 'foo')
        game.join(self.r, 'the valleys', 'bar')

        games = game.games(self.r)

        self.assertItemsEqual(['the hills', 'the valleys'],
                              [g['name'] for g in games.next()['games']])

    def test_games_in_reverse_order(self):
        """
        Most recent games come first.
        """
        game.join(self.r, 'thesis', 'foo')
        game.join(self.r, 'antithesis', 'bar')
        game.join(self.r, 'synthesis', 'baz')

        games = game.games(self.r)

        self.assertEqual(['synthesis', 'antithesis', 'thesis'],
                         [g['name'] for g in games.next()['games']])

    def test_info_id_is_zero_to_start(self):
        info = game.info(self.r, 'game')
        self.assertEquals(0, info.next()['id'])

    def test_info_not_exists(self):
        info = game.info(self.r, 'nonexistent').next()
        self.assertEquals({ 'not_exists': True }, info['state'])

    def test_info_waits_for_id(self):
        """
        The ID passed to info should cause it to hold on a response
        until there are more than that number of updates.
        """
        info = game.info(self.r, 'game', start_info_id=3)

        t = Thread(target=info.next)
        t.start()

        game.join(self.r, 'game', 'first')
        game.join(self.r, 'game', 'second')
        game.join(self.r, 'game', 'third')

        self.assertTrue(t.is_alive())

        game.join(self.r, 'game', 'fourth')

        t.join(1)
        self.assertFalse(t.is_alive())

    def test_info_advances(self):
        info = game.info(self.r, 'blocked')
        info.next()  # pull out the not_exists info

        t = Thread(target=info.next)
        t.start()

        self.assertTrue(t.is_alive())
        time.sleep(0.5)
        self.assertTrue(t.is_alive())

        game.join(self.r, 'blocked', 'some dude')

        t.join(1)
        self.assertFalse(t.is_alive())

    def test_info_advances_beyond_id(self):
        info = game.info(self.r, 'game')
        game.join(self.r, 'game', 'thing one')
        t_all_info = Thread(target=info.next)
        t_all_info.start()
        t_all_info.join(1)
        self.assertFalse(t_all_info.is_alive())

        t_partial_info = Thread(target=info.next)
        t_partial_info.start()
        self.assertTrue(t_partial_info.is_alive())
        time.sleep(0.5)
        self.assertTrue(t_partial_info.is_alive())

        self.assertTrue(game.join(self.r, 'game', 'some dude'))
        t_partial_info.join(1)
        self.assertFalse(t_partial_info.is_alive())


    # def test_triple_landos_moves_to_round_2(self):
    #     self.assertTrue(game.join(self.r, 'game', 'socrates'))
    #     self.assertTrue(game.join(self.r, 'game', 'aristotle'))
    #     self.assertTrue(game.join(self.r, 'game', 'plato'))
    #     self.assertTrue(game.move(self.r, 'game', 'socrates', 'lando'))
    #     self.assertTrue(game.move(self.r, 'game', 'aristotle', 'lando'))
    #     self.assertTrue(game.move(self.r, 'game', 'plato', 'lando'))

    #     info = game.info(self.r, 'game').next()
    #     self.assertIn('status', info)
    #     self.assertDictContainsSubset({
    #             'round': 2,
    #             'players': [{'name':'aristotle',
    #                          'state': 'undecided'},
    #                         {'name':'plato',
    #                          'state': 'undecided'},
    #                         {'name':'socrates',
    #                          'state': 'camp'}]}, info['status'])

    # def test_artifact_destruction(self):
    #     self.assertTrue(game.join(self.r, 'game', 'socrates'))
    #     self.assertTrue(game.join(self.r, 'game', 'aristotle'))

    #     fake_deal(self.r, 'game:deck', 'tube')
    #     fake_deal(self.r, 'game:artifacts.unseen', 'tube')

    #     self.assertTrue(game.move(self.r, 'game', 'socrates', 'lando'))
    #     self.assertTrue(game.move(self.r, 'game', 'aristotle', 'lando'))

    #     info = game.info(self.r, 'game').next()
    #     self.assertDictContainsSubset({'camp': 'socrates', 'id': 1}, info['update'][0])
    #     self.assertDictContainsSubset({'camp': 'aristotle', 'id': 2}, info['update'][1])
    #     self.assertDictContainsSubset({'temple': 'socrates', 'id': 3}, info['update'][2])
    #     self.assertDictContainsSubset({'temple': 'aristotle', 'id': 4}, info['update'][3])
    #     self.assertDictContainsSubset({'round': 1, 'id': 5}, info['update'][4])
    #     self.assertDictContainsSubset({'artifacts.in.play': 'tube', 'id': 6}, info['update'][5])
    #     self.assertDictContainsSubset({'card': 'tube', 'id': 7}, info['update'][6])
    #     self.assertDictContainsSubset({'artifacts.seen.count': 1, 'id': 8}, info['update'][7])
    #     self.assertDictContainsSubset({'moved': 'socrates', 'id': 9}, info['update'][8])
    #     self.assertDictContainsSubset({'moved': 'aristotle', 'id': 10}, info['update'][9])
    #     self.assertDictContainsSubset({'artifacts.destroyed':
    #                                        {'players': ['aristotle', 'socrates'],
    #                                         'card': 'tube',
    #                                         'value': 5},
    #                                    'id': 11 }, info['update'][10])
    #     self.assertDictContainsSubset({'captured':
    #                                        {'players': ['aristotle', 'socrates'],
    #                                         'value': 0,
    #                                         'pot': 0 },
    #                                    'id': 12}, info['update'][11])

    #     self.assertDictContainsSubset({
    #             'pot': 0,
    #             'captured': [],
    #             'artifacts.in.play': [],
    #             'artifacts.seen.count': 1,
    #             'artifacts.destroyed': ['tube'] }, info['status'])

    #     self.assertEquals({'name': 'aristotle',
    #                        'loot': 0,
    #                        'artifacts.captured': [],
    #                        'location': 'camp'},
    #                       game.info(self.r, 'game', 'aristotle').next()['you'])

    #     self.assertEquals({'name': 'socrates',
    #                        'loot': 0,
    #                        'artifacts.captured': [],
    #                        'location': 'camp'},
    #                       game.info(self.r, 'game', 'socrates').next()['you'])

    # def test_artifact_capture(self):
    #     self.assertTrue(game.join(self.r, 'game', 'socrates'))
    #     self.assertTrue(game.join(self.r, 'game', 'aristotle'))

    #     fake_deal(self.r, 'game:deck', 'tube')
    #     fake_deal(self.r, 'game:artifacts.unseen', 'tube')

    #     self.assertTrue(game.move(self.r, 'game', 'socrates', 'han'))
    #     self.assertTrue(game.move(self.r, 'game', 'aristotle', 'lando'))

    #     info = game.info(self.r, 'game').next()

    #     self.assertDictContainsSubset({'camp': 'socrates', 'id': 1}, info['update'][0])
    #     self.assertDictContainsSubset({'camp': 'aristotle', 'id': 2}, info['update'][1])
    #     self.assertDictContainsSubset({'moved': 'socrates', 'id': 3}, info['update'][2])
    #     self.assertDictContainsSubset({'moved': 'aristotle', 'id': 4}, info['update'][3])
    #     self.assertDictContainsSubset({'round': 1, 'id': 5}, info['update'][4])
    #     self.assertDictContainsSubset({'artifacts.in.play': 'tube', 'id': 6}, info['update'][5])
    #     self.assertDictContainsSubset({'card': 'tube', 'id': 7}, info['update'][6])
    #     self.assertDictContainsSubset({'artifacts.seen.count': 1, 'id': 8}, info['update'][7])
    #     self.assertDictContainsSubset({'moved': 'socrates', 'id': 9}, info['update'][8])
    #     self.assertDictContainsSubset({'moved': 'aristotle', 'id': 10}, info['update'][9])
    #     self.assertDictContainsSubset({'artifacts.captured':
    #                                        {'players': 'aristotle',
    #                                         'card': 'tube',
    #                                         'value': 5},
    #                                    'id': 11 }, info['update'][10])
    #     self.assertDictContainsSubset({'captured':
    #                                        {'players': ['aristotle'],
    #                                         'value': 5,
    #                                         'pot': 0 },
    #                                    'id': 12}, info['update'][11])

    #     self.assertDictContainsSubset({
    #             'pot': 0,
    #             'captured': [],
    #             'artifacts.in.play': [],
    #             'artifacts.seen.count': 1,
    #             'artifacts.destroyed': [] }, info['status'])

    #     self.assertEquals({'name': 'aristotle',
    #                        'loot': 5,
    #                        'artifacts.captured': ['tube'],
    #                        'location': 'camp'},
    #                       game.info(self.r, 'game', 'aristotle').next()['you'])

    #     self.assertEquals({'name': 'socrates',
    #                        'loot': 0,
    #                        'artifacts.captured': [],
    #                        'location': 'temple'},
    #                       game.info(self.r, 'game', 'socrates').next()['you'])

    # def test_second_round(self):
    #     self.assertTrue(game.join(self.r, 'game', 'socrates'))
    #     self.assertTrue(game.join(self.r, 'game', 'aristotle'))
    #     self.assertTrue(game.join(self.r, 'game', 'plato'))
    #     self.assertTrue(game.move(self.r, 'game', 'socrates', 'lando'))
    #     self.assertTrue(game.move(self.r, 'game', 'aristotle', 'lando'))
    #     self.assertTrue(game.move(self.r, 'game', 'plato', 'lando'))

    #     info = game.info(self.r, 'game').next()
    #     self.assertIn('status', info)
    #     self.assertEquals(1, len(info['status']['table']))
    #     self.assertDictContainsSubset({
    #             'round': 2,
    #             'players': [{'name':'aristotle',
    #                          'location': 'temple',
    #                          'decision': False},
    #                         {'name':'plato',
    #                          'location': 'temple',
    #                          'decision': False},
    #                         {'name':'socrates',
    #                          'location': 'temple',
    #                          'decision': False}]}, info['status'])

    # def test_full_game(self):
    #     self.assertTrue(game.join(self.r, 'game', 'socrates'))
    #     self.assertTrue(game.join(self.r, 'game', 'aristotle'))

    #     self.assertTrue(game.chat(self.r, 'game', 'aristotle', 'what up soc'))

    #     info = game.info(self.r, 'game').next()
    #     self.assertEquals(3, info['id'])
    #     self.assertEquals(2, len(info['update']))
    #     self.assertDictContainsSubset({'camp': 'socrates', 'id': 1}, info['update'][0])
    #     self.assertDictContainsSubset({'camp': 'aristotle', 'id': 2}, info['update'][1])
    #     self.assertEquals(1, len(info['chat']))
    #     self.assertDictContainsSubset({'speaker': 'aristotle',
    #                                    'message': 'what up soc',
    #                                    'id': 3}, info['chat'][0])
    #     self.assertEquals({
    #             'players': [{'name': 'aristotle',
    #                          'location': 'camp',
    #                          'decision': False},
    #                         {'name': 'socrates',
    #                          'location': 'camp',
    #                          'decision': False}],
    #             'pot': 0,
    #             'round': 0,
    #             'table': [],
    #             'captured': [],
    #             'artifacts.in.play': [],
    #             'artifacts.seen.count': 0,
    #             'artifacts.destroyed': [] }, info['status'])

# Primitive runner!
if __name__ == '__main__':
    unittest.main()
