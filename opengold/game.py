#!/usr/env python

from deck import Treasure, \
                 Hazard, \
                 Artifact, \
                 Deck
from player import Player
from message import State, \
                    EndGame
from uuid import uuid4
from copy import copy


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
        artifact = self.deck.add_artifact()
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

class Round(object):
    """
    A single round of the game.  Players disappear over the course of
    a Round, and loot accumulates.
    """

    def __init__(self, game, players, deck):
        self.players = copy(players)
        self.game = game
        self.deck = deck

        self.table = []  # Cards on the table
        self.pot = 0  # free points floating around

        self._next_deal()

    def _split_loot(self, landos):
        """
        Distribute loot amongst landos and remove treasures and
        artifacts from table.  Take landos out of the round.
        """

        loot = self.pot
        for card in self.table:
            if isinstance(card, Treasure):
                loot += card.value
                self.table.remove(card)
                self.deck.return_card(card)
            elif isinstance(card, Artifact):
                self.table.remove(card)
                if(len(landos) == 1):
                    loot += self.deck.artifact_value()
                    landos[0].take_artifact(card)
                else:
                    #self.game.broadcast(card.destroyed)
                    pass

        remainder = loot % len(landos)
        payout = (loot - remainder) / len(landos)
        self.pot = remainder
        for lando in landos:
            lando.take_gold(payout)
            self.players.remove(lando)

    def _is_over(self):
        """
        Returns True if this round is over, False otherwise.
        """
        hazards = []
        for card in self.table:
            if isinstance(card, Hazard):
                if card.name in hazards:
                    # for player in self.players:
                    #     player.send(card.death)
                    return True
                else:
                    hazards.append(card.name)
        return False

    def _next_deal(self):
        """
        Move round into new deal.
        """
        dealt = self.deck.deal()
        #self.game.broadcast(dealt.broadcast)
        self.table.append(dealt)
        self.deal = Deal(self.players)

    def _return_cards_from_table(self):
        """
        Return cards from the table to the deck.
        """
        for card in self.table:
            self.deck.return_card(card)

    def submit(self, player, move):
        """
        Submit a player's move for this Deal.

        Returns True if the round ended, False otherwise.
        """
        if(self.deal.submit(player, move)):
            if(len(self.deal.landos)):
                self._split_loot(self.deal.landos)

            self.game.broadcast_state(self, self.deal)

            if(self._is_over()):
                self._return_cards_from_table()
                return True
            else:
                self._next_deal()

        return False


class Deal(object):
    """
    A single deal in a game, with an immutable set of players who must each
    make a single choice.  This happens after each card goes down.
    """

    LANDO = 'lando'
    HAN = 'han'

    def __init__(self, players):
        self.players = players

        self.landos = []
        self.hans = []

    def submit(self, player, move):
        """
        Submit a single move for a single player.

        Return True if we're ready to advance, False otherwise
        """
        if(not player in self.players):
            #player.send("You are not in this deal or have already left.")
            pass
        elif((player in self.landos) or (player in self.hans)):
            #player.send("You have already made your choice.")
            pass
        elif(move == self.LANDO):
            #player.send("You are lando")
            self.landos.append(player)
        elif(move == self.HAN):
            #player.send("You are a han solo")
            self.hans.append(player)
        else:
            # player.send("Move '%s' is not a valid move.  Please '%s' or '%s'"
            #             % (move, self.LANDO, self.HAN))
            pass

        if((len(self.landos) + len(self.hans) == len(self.players))):
            return True
        else:
            return False
