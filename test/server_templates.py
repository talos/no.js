# -*- coding: utf-8 -*-

"""
Test server.py with HTML requests.  Starts server and mongrel at start
of test class.
"""

import requests

from helpers import TestOpengoldServer, HOST, unittest

class TestServerTemplates(TestOpengoldServer):
    """
    Tests serving templates directly.
    """

    def new_session(self):
        return requests.session(timeout=1)

    def test_load_game_index_no_games(self):
        s = self.new_session()
        resp = s.get(HOST + '/')
        self.assertRegexpMatches(resp.content, "No games currently available")

    def test_load_game_index_several_games(self):
        s = self.new_session()

        s.post(HOST + '/piper at the gates of dawn/join', data={'player':'barrett'})
        s.post(HOST + '/saucerful of secrets/join', data={'player':'gilmour'})
        s.post(HOST + '/meddle/join', data={'player':'gilmour'})
        resp = s.get(HOST + '/')
        self.assertRegexpMatches(resp.content, "piper at the gates of dawn")
        self.assertRegexpMatches(resp.content, "saucerful of secrets")
        self.assertRegexpMatches(resp.content, "meddle")

    def test_load_nonexistent_game(self):
        s = self.new_session()
        self.assertEquals(404, s.get(HOST + '/nada').status_code)

    def test_join_game_notice(self):
        s = self.new_session()

        s.post(HOST + '/mount/join', data={'player': 'joseph'})

        resp = s.get(HOST + '/mount')
        self.assertRegexpMatches(resp.content, "(?i)joseph joined")

    def test_start_game_notice(self):
        s = self.new_session()

        s.post(HOST + '/mount/join', data={'player': 'joseph'})
        s.post(HOST + '/mount/start')

        resp = s.get(HOST + '/mount')
        self.assertRegexpMatches(resp.content, "(?i)joseph wants to start venturing")

    def test_cant_start_game_alone(self):
        s = self.new_session()

        s.post(HOST + '/cave/join', data={'player': 'hermit'})
        s.post(HOST + '/cave/start')

        resp = s.get(HOST + '/cave')
        self.assertRegexpMatches(resp.content, "(?i)waiting for more players")

    def test_start_game(self):
        jack = self.new_session()
        jill = self.new_session()

        jack.post(HOST + '/hill/join', data={'player': 'jack'})
        jack.post(HOST + '/hill/start')
        jill.post(HOST + '/hill/join', data={'player': 'jill'})
        jill.post(HOST + '/hill/start')

        resp = jack.get(HOST + '/hill')
        self.assertRegexpMatches(resp.content, "(?i)jack and jill entered the hill")
        self.assertRegexpMatches(resp.content, "(?i)\w+ is in the deck")

    def test_move(self):
        jack = self.new_session()
        jill = self.new_session()

        jack.post(HOST + '/hill/join', data={'player': 'jack'})
        jack.post(HOST + '/hill/start')
        jill.post(HOST + '/hill/join', data={'player': 'jill'})
        jill.post(HOST + '/hill/start')
        jack.post(HOST + '/hill/move/lando')

        resp = jack.get(HOST + '/hill')
        self.assertRegexpMatches(resp.content, "(?i)jack made his move")

    def test_next_round_double_landos(self):
        jack = self.new_session()
        jill = self.new_session()

        jack.post(HOST + '/hill/join', data={'player': 'jack'})
        jack.post(HOST + '/hill/start')
        jill.post(HOST + '/hill/join', data={'player': 'jill'})
        jill.post(HOST + '/hill/start')

        jack.post(HOST + '/hill/move/lando')
        jill.post(HOST + '/hill/move/lando')

        resp = jack.get(HOST + '/hill')
        self.assertRegexpMatches(resp.content, "(?i)jack and jill are landos")
        self.assertRegexpMatches(resp.content, "(?i)advancing to round 2")

# Primitive runner!
if __name__ == '__main__':
    unittest.main()
