#!/usr/env python

from deal import Deal
from deck import Hazard, \
                 Artifact, \
                 Treasure
from copy import copy

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
