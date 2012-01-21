# Message types
NOT_YET_STARTED = 'not_yet_started'
IN_PROGRESS = 'in_progress'
FINISHED = 'finished'
MESSAGE = 'message'

def not_yet_started(players):
    return { 'type': NOT_YET_STARTED,
             'players': dict((p.name, {'started': p.started}) for p in players) }

def in_progress(all_players, players_in_play,
           deal, artifacts, table, taken, pot, round_num, you=None):
    """
    Create a python object  with current game state, easily convertible to JSON.
    Generate the game status object.  If there is no `you`, it will
    not contain player-specific data.
    """

    decisions = {}
    for player in all_players:
        decisions[player.name] = {'move': 'lando'}

        # if deal.is_over():
        #     for lando in deal.landos:
        #         decisions[lando.name] = 'lando'
        #     for han in deal.hans:
        #         decisions[han.name] = 'han solo'
        # else:
        for player in players_in_play:
            decisions[player.name] = {'move': 'undecided'}
        for player in deal.landos + deal.hans:
            decisions[player.name] = {'move': 'decided'}

    obj = {
        'type' : IN_PROGRESS,
        'players' : decisions,
        'table': [card.name for card in table],
        'taken': [card.name for card in taken],
        'pot': pot,
        'round': round_num,
        'artifacts': [artifact.name for artifact in artifacts]
        }

    if you:
        obj['you'] = you.name
        obj['loot'] = you.loot

    return obj

def finished(players, round_num):
    """
    A message with endgame state, easily convertible to JSON.
    """
    # scores = {}
    # for player in players:
    #     scores[player.name] = {
    #         'loot' : player.loot,
    #         'artifacts' : [artifact.name for artifact in player.artifacts]
    #         }
        #return { 'finished': { 'scores' : scores } }

    return {
        'type': FINISHED,
        'players': dict((p.name, {
                    'loot' : p.loot,
                    'artifacts' : [artifact.name for artifact in p.artifacts]
                    }) for p in players)
        }

def chat(speaker, message):
    """
    A chat message.
    """
    return {
        'type': MESSAGE,
        'speaker': speaker,
        'message': message
        }
