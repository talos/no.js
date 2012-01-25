from itertools import product
from collections import namedtuple

Treasure = namedtuple('treasure', ['name', 'value'])
Hazard = namedtuple('hazard', 'name')
Artifact = namedtuple('artifact', 'name')

_TREASURES = [Treasure(name=str(value), value=value)
             for value in [1,2,3,4,5,5,7,7,9,11,11,13,14,15,17]]
_HAZARDS = [Hazard(name)
           for name, i in product(['bitches', 'spiders', 'snakes', 'fire', 'bricks'],
                                  xrange(3))]
_ARTIFACTS = [Artifact(name)
             for name in ['zefrim cockring', 'shrek', 'tube', 'nazi', 'gingerbread man']]

_DECK = _TREASURES + _HAZARDS + _ARTIFACTS

TREASURES = range(0, len(_TREASURES))
HAZARDS = range(len(_TREASURES), len(_TREASURES) + len(_HAZARDS))
ARTIFACTS = range(len(_TREASURES) + len(_HAZARDS), len(_DECK))

def get_card(card_idx):
    """
    Get a card object by index.
    """
    return _DECK[int(card_idx)]
