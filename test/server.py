"""
Test server.py.  Restarts server & mongrel each time.
"""

import unittest
import subprocess
import requests
import redis
import json
import time

HOST = "http://localhost:6767"
DB_NAME = 'TestServer'
JSON_HEADER = {'content-type': 'application/json'}

class TestServerJSON(unittest.TestCase):
    """
    Test JSON methods on the server.  Does not hit the template side of things.
    """

    @classmethod
    def setUpClass(cls):
        """Start up the server
        """
        cls.server = subprocess.Popen('m2sh start -host localhost', shell=True)
        cls.app = subprocess.Popen('python opengold/server.py %s' % DB_NAME, shell=True)
        print "Waiting for server to start"
        time.sleep(2)
        print "Finished waiting for server to start"

    @classmethod
    def tearDownClass(cls):
        """
        Shut down the server
        """
        cls.app.terminate()
        cls.app.wait()
        subprocess.Popen('m2sh stop -host localhost', shell=True)

    def setUp(self):
        """
        Clean DB entirely between tests.
        """
        redis.StrictRedis(db=DB_NAME).flushdb()

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
                             'decision': False,
                             'location': 'camp'},
                           {'name': 'jill',
                            'decision': False,
                            'location': 'camp'}]
        self.assertEquals(expected_players, jack_info['status']['players'])
        self.assertEquals(expected_players, jill_info['status']['players'])
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
