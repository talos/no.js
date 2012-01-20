from itertools import product
from random import shuffle


class Card(object):
    """
    Generic card.
    """

    @property
    def name(self):
        return self._name


class Treasure(Card):
    """
    Treasure card, initialize w/ value.

    Treasure.value
    """

    def __init__(self, value):
        self._name = value
        self._value = value

    @property
    def value(self):
        return self._value


class Hazard(Card):
    """
    Causes death when paired.
    """

    def __init__(self, name):
        self._name = name


class Artifact(Card):
    """
    Destroyed when taken.
    """

    def __init__(self, name):
        self._name = name


class Deck(object):
    """
    A deck of cards
    """

    def __init__(self):
        self._deck = []
        self._artifacts_in_play = []
        self._artifacts_seen = 0

        # One of each treasure card
        # 1 - 4 * 1
        # 5 * 2
        # 7 * 2
        # 9 * 1
        # 11 * 2
        # 13 - 15 * 1
        # 17 * 1

        for value in [1,2,3,4,5,5,7,7,9,11,11,13,14,15,17]:
            self._deck.append(Treasure(value))

        # Three of each hazard
        # for tup in [('bitches', 'bitched'),
        #             ('spiders', 'stung'),
        #             ('snakes', 'snaked'),
        #             ('fire', 'burned'),
        #             ('bricks', 'bricked')]:

        for name, i in product(['bitches', 'spiders', 'snakes', 'fire', 'bricks'], xrange(3)):
            self._deck.append(Hazard(name))

        # Artifacts not in play to start
        # self._artifacts = [Artifact(*tup) for tup in [
        #         ('zefrim cockring', 'cockring in play', 'cockring blown'),
        #         ('shrek', 'shreck is in the deck', 'shreck shredded'),
        #         ('tube', 'tube in play', 'tube out of play'),
        #         ('nazi', 'nazi in play', 'nazy out of play'),
        #         ('gingerbread man', 'ginger in play', 'ginger broken')]]

        self._artifacts = [Artifact(name) for name in
                           ['zefrim cockring', 'shrek', 'tube', 'nazi', 'gingerbread man']]

        shuffle(self._artifacts)

    def deal(self):
        """
        Pop off a single random card.
        """
        shuffle(self._deck)
        dealt = self._deck.pop()
        if(isinstance(dealt, Artifact)):
            self._artifacts_in_play.remove(dealt)
            self._artifacts_seen += 1
        return dealt

    def add_artifact(self):
        """
        Add a single artifact.
        """
        artifact = self._artifacts.pop()
        self._artifacts_in_play.append(artifact)
        self._deck.append(artifact)

    @property
    def artifact_value(self):
        """
        Retrieve the value of an artifact at this point.
        """
        if self._artifacts_seen <= 3:
            return 5
        else:
            return 10

    def return_card(self, card):
        """
        Return card to deck.
        """
        if isinstance(card, Artifact):
            self._artifacts_in_play.append(card)
        self._deck.append(card)

    @property
    def artifacts(self):
        """
        Get the artifacts currently in the deck, excluding those on
        the table.
        """
        return self._artifacts_in_play
