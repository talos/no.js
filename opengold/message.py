import json

class Status(object):
    """
    A message with current game state, easily convertible to JSON.
    """

    def __init__(self, you, all_players, players_in_play,
                 deal, artifacts, table, pot, round_num):
        """
        Generate the game status object.  If there is no `you`, it will
        not contain player-specific data.
        """
        decisions = {}
        for player in all_players:
            decisions[player.name] = 'camped'

        if deal.is_over:
            for lando in deal.landos:
                decisions[lando.name] = 'lando'
            for han in deal.hans:
                decisions[han.name] = 'han solo'
        else:
            for player in players_in_play:
                decisions[player.name] = 'undecided'
            for player in deal.landos + deal.hans:
                decisions[player.name] = 'decided'

        self.obj = {
            'decisions' : decisions,
            'table': [card.name for card in table],
            'pot': pot,
            'round': round_num,
            'artifacts': [artifact.name for artifact in artifacts]
            }

        if you:
            self.obj.put('you', you.name)
            self.obj.put('loot', you.loot)

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
