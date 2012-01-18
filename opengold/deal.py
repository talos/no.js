#!/usr/env python

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
