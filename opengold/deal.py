#!/usr/env python

LANDO = 'lando'
HAN = 'han'

class Deal(object):
    """
    A single deal in a game, with an immutable set of players who must each
    make a single choice.  This happens after each card goes down.
    """

    def __init__(self, players):
        self._players = players
        self._landos = []
        self._hans = []

    def submit(self, player, move):
        """
        Submit a single move for a single player.

        Return True if the move could be submitted, False otherwise.
        """
        if((player.name in self._players.keys()) and
           (not player in self._hans) and
           (not player in self._landos)):
            if move == LANDO:
                self._landos.append(player)
                return True
            elif move == HAN:
                self._hans.append(player)
                return True

        return False

    def is_over(self):
        """
        Returns True if this round is done, False otherwise.
        """
        return len(self._landos) + len(self._hans) == len(self._players)

    @property
    def landos(self):
        """
        Return the Landos from this deal.
        """
        return self._landos

    @property
    def hans(self):
        """
        Return the Hans in this deal.
        """
        return self._hans
