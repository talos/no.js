"""
Test server.py.  Restarts server & mongrel each time.
"""

import unittest
import subprocess
import requests
import json
import time

HOST = "http://localhost:6767"


class TestServer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Start up the server
        """
        cls.server = subprocess.Popen('m2sh start -host localhost', shell=True)
        cls.app = subprocess.Popen('python opengold/server.py', shell=True)
        print "Waiting for server to start"
        time.sleep(3)
        print "Finished waiting for server to start"

    @classmethod
    def tearDownClass(cls):
        """
        Shut down the server
        """
        cls.app.terminate()
        cls.app.wait()
        subprocess.Popen('m2sh stop -host localhost', shell=True)

    def test_new_game(self):
        """
        Jack and Jill join a hill...
        """
        jack = requests.session()
        jill = requests.session()

        self.assertEquals(200, jack.post(HOST + '/hill/join/jack').status_code)
        self.assertEquals(200, jill.post(HOST + '/hill/join/jill').status_code)

        self.assertEquals({
                'type': 'not_yet_started',
                'players': {
                    'jack': { 'started': False },
                    'jill': { 'started': False }
                    }}, json.loads(jack.get(HOST + '/hill').content))

        self.assertEquals(200, jack.post(HOST + '/hill/start').status_code)

        self.assertEquals({
                'type': 'not_yet_started',
                'players': {
                    'jack': { 'started': True },
                    'jill': { 'started': False }
                    }}, json.loads(jack.get(HOST + '/hill').content))

        self.assertEquals(200, jill.post(HOST + '/hill/start').status_code)

        status = json.loads(jack.get(HOST + '/hill').content)
        artifacts = status.pop('artifacts')
        self.assertTrue(len(artifacts) is 0 or len(artifacts) is 1)
        self.assertEquals(1, len(status.pop('table')))
        self.assertEquals({
                'type': 'in_progress',
                'round' : 1,
                'pot': 0,
                'taken' : [],
                'you' : 'jack',
                'loot' : 0,
                'players': {
                    'jack': { 'move': 'undecided' },
                    'jill': { 'move': 'undecided' }
                    }}, status)

        self.assertEquals(200, jack.post(HOST + '/hill/move/lando').status_code)
        self.assertEquals(200, jill.post(HOST + '/hill/move/lando').status_code)

        # At this point, the game should have advanced to the next round.

# Primitive runner!
if __name__ == '__main__':
    unittest.main()
