import json

class State(object):
    """
    A message with current game state, easily convertible to JSON.
    """

    def __init__(self, you, players, landos, hans, deck, table, pot, round_num):
        decisions = {}
        for player in players:
            decisions[player.name] = 'camped'
        for lando in landos:
            decisions[lando.name] = 'lando'
        for han in hans:
            decisions[han.name] = 'han solo'
        self.obj = {
            'decisions' : decisions,
            'you' : you.name,
            'loot': you.loot,
            'table': [card.name for card in table],
            'pot': pot,
            'round': round_num,
            'artifacts': [artifact.name for artifact in deck.artifacts_in_play],
            }

    def to_json(self):
        return json.dumps(self.obj)


class EndGame(object):
    """
    A message with endgame state, easily convertible to JSON.
    """

    def __init__(self, players):
        self.obj = {}
        for player in players:
            self.obj[player.name] = {
                'loot' : player.loot,
                'artifacts' : [artifact.name for artifact in player.artifacts]
                }

    def to_json(self):
        return json.dumps(self.obj)
