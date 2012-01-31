# -*- coding: utf-8 -*-

"""
Test server.py with JSON requests.  Starts server and mongrel at start
of test class.
"""

import requests
from requests import async
import gevent
import json
import urllib2

from helpers import TestOpengoldServer, HOST, unittest

JSON_HEADER = {'accept': 'application/json, text/javascript'}

class TestServerJSON(TestOpengoldServer):
    """
    Test JSON methods on the server.  Does not hit the template side of things.
    """

    def json_session(self):
        """
        Produce a JSON-only session.
        """
        return requests.session(headers=JSON_HEADER)

    def test_join_game(self):
        """
        Jack and Jill join a hill...
        """
        jack = self.json_session()
        jill = self.json_session()

        self.assertEquals(200, jack.post(HOST + '/hill/join',
                                         data={'player':'jack'}).status_code)
        self.assertEquals(200, jill.post(HOST + '/hill/join',
                                         data={'player':'jill'}).status_code)

        jack_info = json.loads(jack.get(HOST + '/hill').content)
        jill_info = json.loads(jill.get(HOST + '/hill').content)
        expected_players = [{'name': 'jack',
                             'state': 'joined'},
                           {'name': 'jill',
                            'state': 'joined'}]
        self.assertEquals(expected_players, jack_info['state']['players'])
        self.assertEquals(expected_players, jill_info['state']['players'])
        self.assertEquals('jack', jack_info['you']['name'])
        self.assertEquals('jill', jill_info['you']['name'])

    def test_join_game_needs_name(self):
        s = self.json_session()

        self.assertEquals(400, s.post(HOST + '/game/join').status_code)

    def test_join_game_only_once(self):
        s = self.json_session()

        s.post(HOST + '/somewhere/join', data={'player':'sir clicksalot'})
        self.assertEquals(400, s.post(HOST + '/somewhere/join',
                                      data={'player':'sir clicksalot'}).status_code)

    def test_join_game_with_many_names_fails(self):
        s = self.json_session()

        s.post(HOST + '/somewhere/join', data={'player':'joseph'})
        self.assertEquals(400, s.post(HOST + '/somewhere/join',
                                      data={'player':'mary'}).status_code)

    def test_join_multiple_games(self):
        s = self.json_session()

        self.assertEquals(200, s.post(HOST + '/here/join', data={'player':'paul'}).status_code)
        self.assertEquals(200, s.post(HOST + '/there/join', data={'player':'john'}).status_code)
        self.assertEquals(200, s.post(HOST + '/and everywhere/join', data={'player':'ringo'}).status_code)

    def test_game_list_names_most_recent(self):
        """
        Most recent games should be first.
        """
        s = self.json_session()

        s.post(HOST + '/blackbird/join', data={'player':'paul'})
        s.post(HOST + '/yellow submarine/join', data={'player':'ringo'})
        s.post(HOST + '/sexy sadie/join', data={'player':'john'})

        self.assertEquals(['sexy sadie', 'yellow submarine', 'blackbird'],
                          [g['name'] for g in json.loads(s.get(HOST + '/').content)['games']])

    def test_xss_names(self):
        """
        Totally arbitrary text is allowed in game names.  Filtering is
        done through templating.
        """
        s = self.json_session()

        xss = "<script type='text/javascript'>document.write('bullshit')</script>"
        xss_quoted = urllib2.quote(xss, '')

        self.assertEquals(
            200,
            s.post(HOST + '/%s/join' % xss_quoted, data={'player':'bastard'}).status_code)

        self.assertEquals(xss, json.loads(s.get(HOST + '/').content)['games'][0]['name'])

    def test_unicode_game_name(self):
        """
        Hehe.
        """
        s = self.json_session()

        self.assertEquals(
            200,
            s.post(HOST + u"/☃/join", data={'player':'snowman'}).status_code)

        self.assertEquals({'names': [u"☃"]},
                          json.loads(s.get(HOST + '/').content))

    def test_unicode_player_name(self):
        """
        Sno man ftw
        """
        s = self.json_session()

        self.assertEquals(
            200,
            s.post(HOST + "/iceberg/join", data={'player':u"☃"}).status_code)
        resp = s.get(HOST + "/iceberg").content
        self.assertEquals(u"☃", json.loads(resp)['you']['name'])

    def test_long_poll_game_list(self):
        """
        When no new games have been made after an ID, then calls for
        the list of games should hang.
        """
        s = self.json_session()

        resp = s.get(HOST + '/')
        last_id = json.loads(resp.content)['id']

        poll = async.send(async.get(HOST + "/", params={"id":last_id}))
        gevent.sleep(0.5)
        self.assertFalse(poll.successful())

        s.post(HOST + '/alpha/join', data={'player':'honcho'})
        poll.join()
        self.assertTrue(poll.successful())

    def test_long_poll_nonexistent_game(self):
        """
        Request for info about nonexistent game using the ID initially
        returned should hang after initial response, until something
        happens.
        """
        s = self.json_session()

        initial_id = json.loads(requests.get(HOST + '/beta').content)['id']
        poll = async.send(async.get(HOST + "/beta", params={"id":initial_id}))

        gevent.sleep(0.5)
        self.assertFalse(poll.successful())

        s.post(HOST + "/beta/join", data={"player":"django"})
        poll.join()
        self.assertTrue(poll.successful())

    def test_long_poll_existing_game(self):
        """
        When nothing has happened since an ID, JSON calls for info after a
        specific ID should hang.
        """
        s = self.json_session()

        s.post(HOST + "/gaga/join", data={"player":"django"})
        last_id = json.loads(s.get(HOST + "/gaga").content)['id']

        poll = async.send(async.get(HOST + "/gaga", params={"id":last_id}))

        # TODO sleeping before this causes immediate resolution, but
        # actually stopping with a set_trace properly delays
        # resolution. ???
        # gevent.sleep(0.5)
        self.assertFalse(poll.successful())

        s.post(HOST + '/gaga/start')
        poll.join()
        self.assertTrue(poll.successful())


    # def test_new_game(self):
    #     self.assertEquals({
    #             'type': 'not_yet_started',
    #             'players': [{'name': 'jill', 'started': False },
    #                         {'name': 'jack', 'started': False }]},
    #                       json.loads(jack.get(HOST + '/hill/status').content))

    #     self.assertEquals(200, jack.post(HOST + '/hill/start').status_code)

    #     self.assertEquals({
    #             'type': 'not_yet_started',
    #             'players': [{'name': 'jill', 'started': False },
    #                         {'name': 'jack', 'started': True }]},
    #                       json.loads(jack.get(HOST + '/hill/status').content))

    #     self.assertEquals(200, jill.post(HOST + '/hill/start').status_code)

    #     status = json.loads(jack.get(HOST + '/hill/status').content)
    #     artifacts = status.pop('artifacts')
    #     self.assertTrue(len(artifacts) is 0 or len(artifacts) is 1)
    #     self.assertEquals(1, len(status.pop('table')))
    #     self.assertEquals({
    #             'type': 'in_progress',
    #             'round' : 1,
    #             'pot': 0,
    #             'captured' : [],
    #             'you' : 'jack',
    #             'loot' : 0,
    #             'players': [{'name': 'jill', 'move': 'undecided' },
    #                         {'name': 'jack', 'move': 'undecided'}]}, status)

    #     self.assertEquals(200, jack.post(HOST + '/hill/move',
    #                                      data={'move':'lando'}).status_code)
    #     self.assertEquals(200, jill.post(HOST + '/hill/move',
    #                                      data={'move':'lando'}).status_code)

        # At this point, the game should have advanced to the next round.

# Primitive runner!
if __name__ == '__main__':
    unittest.main()
