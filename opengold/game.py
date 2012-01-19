#!/usr/env python

import uuid

from deck import Deck
from round import Round
from player import Player
from message import Status

MAX_ROUNDS = 5

NOT_STARTED = 0
IN_PROGRESS = 1
FINISHED = 2

class Game(object):

    def __init__(self, name):
        """
        Generate a new game with the specified name.
        """
        self._players = {}
        self._victors = []
        self._deck = Deck()
        self._name = name
        self._round_num = 0
        self._state = NOT_STARTED
        self._advance_state_id()

    def _advance_state_id(self):
        self._state_id = str(uuid.uuid4())

    def _next_round(self):
        """
        Advance to the next round.  We have to add an artifact into the deck.
        """
        self._round_num += 1
        self._deck.add_artifact()
        self._round = Round(self._players, self._deck)

    def _determine_victors(self):
        """
        Return the players with the most points, breaking tie with
        artifacts.  Ties only happen if there are identical points and
        artifacts.
        """
        by_loot = {}
        for player in self._players:
            loot = player.loot
            by_loot[loot] = by_loot.get(loot, []) + [player]

        most_loot = sorted(by_loot.keys(), reverse=True)[0]
        candidates = by_loot[most_loot]

        by_artifacts = {}
        for candidate in candidates:
            artifacts = len(candidate.artifacts)
            by_artifacts[artifacts] = by_artifacts.get(artifacts, []) + [candidate]
        most_artifacts = sorted(by_artifacts.keys(), reverse=True)[0]

        return by_artifacts[most_artifacts]

    def add_player(self, player_name):
        """
        Add a player to the game.  Returns a Player object if they have been
        added, or None otherwise.
        """
        if (self._round_num is 0) and (not player_name in self._players.keys()):
            self._players[player_name] = Player(player_name)
            return True
        else:
            return False

    def start(self):
        """
        Start the game.  This stops new players from joining.  Returns
        True if the game has been started, False otherwise.
        """
        if self._round_num is 0 and len(self._players) > 1:
            self._next_round()
            self._state = IN_PROGRESS
            return True
        else:
            return False

    @property
    def state_id(self):
        """
        Return the internal state as a string.  This is useful as a
        check to see if anything has happened in this game.
        """
        return self._state_id

    def get_status(self, player):
        """
        The game's current status.  If None is passed for player, then
        no player-specific data will be returned.
        """
        return Status(
            player,
            self._players,
            self._round.players_in_play,
            self._round.deal,
            self._deck.artifacts_in_play,
            self._table,
            self._pot,
            self._round_num)

    def submit(self, player_name, move):
        """
        Submit a move for the specified player in the current round.
        Returns True if the move was submitted, False otherwise.
        """
        player = self._players.get(player_name)

        if player:
            if self._state == IN_PROGRESS and self._round.submit(player, move):
                if self._round.is_over():
                    if(self._round_num < MAX_ROUNDS):
                        self._next_round()
                    else:
                        self._victors = self._determine_victors()
                        self._state = FINISHED

                self._advance_state_id()
                return True

        return False
