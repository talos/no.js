#!/usr/env python

from deck import Deck
from round import Round
from message import State, \
                    EndGame
from uuid import uuid4


class Game(object):
    MAX_ROUNDS = 5

    def __init__(self, players):
        self.players = players
        self.victors = []
        # TODO make sure players don't have dupe names?
        self.deck = Deck()
        self.id = uuid4()
        self.round_num = 0

        self._next_round()

    def _next_round(self):
        """
        Advance to the next round.  We have to add an artifact into the deck.
        """
        self.round_num += 1
        self.deck.add_artifact()
        self.round = Round(self, self.players, self.deck)

    def _determine_victors(self):
        """
        Return the players with the most points, breaking tie with
        artifacts.  Ties only happen if there are identical points and
        artifacts.
        """
        by_loot = {}
        for player in self.players:
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

    def submit(self, player, move):
        """
        Submit a move for the specified player in the current round.
        Returns False if the game is not done, True otherwise.
        """
        if(self.round.submit(player, move)):
            if(self.round_num < self.MAX_ROUNDS):
                self._next_round()
            else:
                self.victors = self._determine_victors()
                self.broadcast_end_game()
                return True

        return False

    def broadcast_state(self, round, deal):
        """
        Broadcast state for each player
        """
        for player in self.players:
            player.send(
                State(player,
                      self.players,
                      deal.landos,
                      deal.hans,
                      self.deck,
                      round.table,
                      round.pot,
                      self.round_num).to_json())

    def broadcast_end_game(self):
        """
        Broadcast the endgame.
        """
        end_game = EndGame(self.players)
        for player in self.players:
            player.send(end_game.to_json())
