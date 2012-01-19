#!/usr/bin/env python

from game import Game

class Database(object):

    def __init__(self):
        self._games = {}

    def get_game(self, game_name):
        """
        Retrieve a game by name.  Creates a new game by that name
        if there is none.
        """
        game = self._games.get(game_name)
        if not game:
            game = Game(game_name)
            self._games[game_name] = game
        return game
