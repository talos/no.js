from random import shuffle

class Card(object):
    """
    Generic card.
    """
    pass


class Treasure(Card):
    """
    Treasure card, initialize w/ value.

    Treasure.value
    """

    def __init__(self, value):
        self.name = value
        self.value = value


class Hazard(Card):
    """
    Causes death when paired.

    Hazard.name
    Hazard.death
    """

    def __init__(self, name, death):
        self.name = name
        self.death = death


class Artifact(Card):
    """
    Destroyed when taken.

    Artifact.name
    Artifact.in_deck
    Artifact.destroyed
    """

    def __init__(self, name, in_deck, destroyed):
        self.name = name
        self.in_deck = in_deck
        self.destroyed = destroyed


class Deck(object):
    """
    A deck of cards
    """

    def __init__(self):
        self.deck = []
        self.artifacts_in_play = []
        self.artifacts_seen = 0

        # One of each treasure card
        # 1 - 4 * 1
        # 5 * 2
        # 7 * 2
        # 9 * 1
        # 11 * 2
        # 13 - 15 * 1
        # 17 * 1

        for value in [1,2,3,4,5,5,7,7,9,11,11,13,14,15,17]:
            self.deck.append(Treasure(value))

        # Three of each hazard
        for tup in [('bitches', 'bitched'),
                    ('spiders', 'stung'),
                    ('snakes', 'snaked'),
                    ('fire', 'burned'),
                    ('bricks', 'bricked')]:
            for i in range(3):
                self.deck.append(Hazard(*tup))

        # Artifacts not in play to start
        self.artifacts = [Artifact(*tup) for tup in [
                ('zefrim cockring', 'cockring in play', 'cockring blown'),
                ('shrek', 'shreck is in the deck', 'shreck shredded'),
                ('tube', 'tube in play', 'tube out of play'),
                ('nazi', 'nazi in play', 'nazy out of play'),
                ('gingerbread man', 'ginger in play', 'ginger broken')]]
        shuffle(self.artifacts)

    def deal(self):
        """
        Pop off a single random card.
        """
        shuffle(self.deck)
        dealt = self.deck.pop()
        if(isinstance(dealt, Artifact)):
            self.artifacts_seen += 1
        return dealt

    def add_artifact(self):
        """
        Add a single artifact.
        """
        artifact = self.artifacts.pop()
        self.artifacts_in_play.append(artifact)
        self.deck.append(artifact)

    def artifact_value(self):
        """
        Retrieve the value of an artifact at this point.
        """
        if self.artifacts_seen <= 3:
            return 5
        else:
            return 10

    def return_card(self, card):
        """
        Return card to deck.
        """
        self.deck.append(card)
