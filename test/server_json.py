# -*- coding: utf-8 -*-

"""
Test server.py with JSON requests.  Starts server and mongrel at start
of test class.
"""

import requests
from requests import async
import json
import urllib2

from helpers import TestOpengoldServer, HOST, unittest

JSON_HEADER = {'content-type': 'application/json'}

class TestServerJSON(TestOpengoldServer):

    """
    Test JSON methods on the server.  Does not hit the template side of things.
    """
    def test_join_game(self):
        """
        Jack and Jill join a hill...
        """
        jack = requests.session()
        jill = requests.session()

        self.assertEquals(200, jack.post(HOST + '/hill/join',
                                         data={'player':'jack'}).status_code)
        self.assertEquals(200, jill.post(HOST + '/hill/join',
                                         data={'player':'jill'}).status_code)

        jack_info = json.loads(jack.get(HOST + '/hill', headers=JSON_HEADER).content)
        jill_info = json.loads(jill.get(HOST + '/hill', headers=JSON_HEADER).content)
        expected_players = [{'name': 'jack',
                             'state': 'joined'},
                           {'name': 'jill',
                            'state': 'joined'}]
        self.assertEquals(expected_players, jack_info['state']['players'])
        self.assertEquals(expected_players, jill_info['state']['players'])
        self.assertEquals('jack', jack_info['you']['name'])
        self.assertEquals('jill', jill_info['you']['name'])

    def test_join_game_needs_name(self):
        s = requests.session()

        self.assertEquals(400, s.post(HOST + '/game/join').status_code)

    def test_join_game_only_once(self):
        s = requests.session()

        s.post(HOST + '/somewhere/join', data={'player':'sir clicksalot'})
        self.assertEquals(400, s.post(HOST + '/somewhere/join',
                                      data={'player':'sir clicksalot'}).status_code)

    def test_join_game_with_many_names_fails(self):
        s = requests.session()

        s.post(HOST + '/somewhere/join', data={'player':'joseph'})
        self.assertEquals(400, s.post(HOST + '/somewhere/join',
                                      data={'player':'mary'}).status_code)

    def test_join_multiple_games(self):
        s = requests.session()

        self.assertEquals(200, s.post(HOST + '/here/join', data={'player':'paul'}).status_code)
        self.assertEquals(200, s.post(HOST + '/there/join', data={'player':'john'}).status_code)
        self.assertEquals(200, s.post(HOST + '/and everywhere/join', data={'player':'ringo'}).status_code)

    def test_game_list(self):
        s = requests.session()

        s.post(HOST + '/sexy sadie/join', data={'player':'john'})
        s.post(HOST + '/blackbird/join', data={'player':'paul'})
        s.post(HOST + '/yellow submarine/join', data={'player':'ringo'})

        self.assertEquals({'names': ['blackbird', 'sexy sadie', 'yellow submarine']},
                          json.loads(s.get(HOST + '/', headers=JSON_HEADER).content))

    def test_xss(self):
        """
        Totally arbitrary text is allowed in titles.  Filtering is
        done using .text() later on from the JSON object.
        """
        s = requests.session()

        xss = "<script type='text/javascript'>document.write('bullshit')</script>"
        xss_quoted = urllib2.quote(xss, '')

        self.assertEquals(
            200,
            s.post(HOST + '/%s/join' % xss_quoted, data={'player':'bastard'}).status_code)

        self.assertEquals(
            {'names': [xss]},
            json.loads(s.get(HOST + '/', headers=JSON_HEADER).content))

    def test_unicode_game_name(self):
        """
        Hehe.
        """
        s = requests.session()

        self.assertEquals(
            200,
            s.post(HOST + u"/☃/join", data={'player':'snowman'}).status_code)

        self.assertEquals({'names': [u"☃"]},
                          json.loads(s.get(HOST + '/', headers=JSON_HEADER).content))

    def test_unicode_player_name(self):
        """
        Sno man ftw
        """
        s = requests.session()

        self.assertEquals(
            200,
            s.post(HOST + "/iceberg/join", data={'player':u"☃"}).status_code)
        resp = s.get(HOST + "/iceberg", headers=JSON_HEADER).content
        self.assertEquals(u"☃", json.loads(resp)['you']['name'])

    def test_long_poll(self):
        """
        When nothing has happened since an ID, JSON calls for info after a
        specific ID should hang.
        """
        s = requests.session()

        s.post(HOST + "/game/join", data={"player":"django"})
        last_id = json.loads(s.get(HOST + "/game", headers=JSON_HEADER).content)['id']

        import pdb
        pdb.set_trace()

        poll = async.get(HOST + "/game", headers=JSON_HEADER, data={"id":last_id})

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
