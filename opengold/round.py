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

    def __init__(self, players, deck):
        self._players = copy(players)
        self._deck = deck

        self._table = []
        self._taken = []
        self._pot = 0

        self._next_deal()

    def _split_loot(self, landos):
        """
        Distribute loot amongst landos and remove treasures and
        artifacts from table.  Take landos out of the round.
        """

        loot = self._pot
        for card in self._table:
            if isinstance(card, Treasure):
                loot += card.value
                self._table.remove(card)
                self._taken.append(card)
                self._deck.return_card(card)
            elif isinstance(card, Artifact):
                self._table.remove(card)
                if(len(landos) == 1):
                    loot += self._deck.artifact_value
                    landos[0].take_artifact(card)

        remainder = loot % len(landos)
        payout = (loot - remainder) / len(landos)
        self._pot = remainder
        for lando in landos:
            lando.take_gold(payout)
            self._players.remove(lando)

    def _next_deal(self):
        """
        Move round into new deal.
        """
        dealt = self._deck.deal()
        self._table.append(dealt)
        self._deal = Deal(self._players)

    def _return_cards_from_table(self):
        """
        Return cards from the table to the deck.
        """
        for card in self._table:
            self._deck.return_card(card)

    @property
    def players_in_play(self):
        """
        Return the players still in this round.
        """
        return self._players

    @property
    def deal(self):
        """
        Return the current deal.
        """
        return self._deal

    def submit(self, player, move):
        """
        Submit a player's move for this Deal.

        Returns True if their move was valid, False otherwise.
        """
        valid_move = self._deal.submit(player, move)
        if(valid_move):
            if(self._deal.is_over()):
                landos = self._deal.landos
                if(len(landos) > 0):
                   self._split_loot(landos)

                if(self.is_over()):
                    self._return_cards_from_table()
                else:
                    self._next_deal()

        return valid_move

    def is_over(self):
        """
        Returns True if this round is over because everyone left or
        there were multiple hazards, False otherwise.
        """
        if len(self._players) is 0:
            return True

        hazards = []
        for card in self._table:
            if isinstance(card, Hazard):
                if card.name in hazards:
                    return True
                else:
                    hazards.append(card.name)
        return False

    @property
    def table(self):
        """
        A list of cards on the table.  All treasures here still have face value.
        """
        return self._table

    @property
    def pot(self):
        """
        The number of free points floating around
        """
        return self._pot

    @property
    def taken(self):
        """
        Treasures captured, kept on table for reference
        """
        return self._taken
