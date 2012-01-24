from itertools import product
from random import shuffle

TREASURES = [str(i) for i in [1,2,3,4,5,5,7,7,9,11,11,13,14,15,17]]
HAZARDS = ['bitches', 'spiders', 'snakes', 'fire', 'bricks']
ARTIFACTS = ['zefrim cockring', 'shrek', 'tube', 'nazi', 'gingerbread man']

def card_type(card):
    """
    Get the type of a card.  Either 'treasure', 'hazard', or 'artifact'.
    """
    if card in TREASURES:
        return 'treasure'
    elif card in HAZARDS:
        return 'hazard'
    elif card in ARTIFACTS:
        return 'artifact'
    else:
        raise ValueError('Unknown card type %s' % card)

def generate_deck():
    """
    Generate the initial deck as a list.  It has no artifacts, and is
    not shuffled.  You must remember to pick random index items from it.
    """
    return TREASURES + [name for name, i in product(HAZARDS, xrange(3))]

def generate_artifacts():
    """
    Generate artifacts that must be added to the deck as a list. It is
    already shuffled.
    """
    artifacts = ARTIFACTS
    shuffle(artifacts)
    return artifacts
