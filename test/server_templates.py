# -*- coding: utf-8 -*-

"""
Test server.py with HTML requests.  Starts server and mongrel at start
of test class.
"""

import requests

from helpers import TestOpengoldServer, HOST, unittest

class TestServerTemplates(TestOpengoldServer):
    """
    Test JSON methods on the server.  Does not hit the template side of things.
    """

    def test_load_game_index_no_games(self):
        s = requests.session()
        resp = s.get(HOST + '/')
        self.assertRegexpMatches(resp.content, "No games currently available")

    def test_load_game_index_several_games(self):
        s = requests.session()

        s.post(HOST + '/piper at the gates of dawn/join', data={'player':'barrett'})
        s.post(HOST + '/saucerful of secrets/join', data={'player':'gilmour'})
        s.post(HOST + '/meddle/join', data={'player':'gilmour'})
        resp = s.get(HOST + '/')
        self.assertRegexpMatches(resp.content, "piper at the gates of dawn")
        self.assertRegexpMatches(resp.content, "saucerful of secrets")
        self.assertRegexpMatches(resp.content, "meddle")

    def test_load_nonexistent_game(self):
        s = requests.session()
        self.assertEquals(404, s.get(HOST + '/nada').status_code)

# Primitive runner!
if __name__ == '__main__':
    unittest.main()
