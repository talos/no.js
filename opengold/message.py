# Message types
NOT_YET_STARTED = 'not_yet_started'
IN_PROGRESS = 'in_progress'
FINISHED = 'finished'
MESSAGE = 'message'

def not_yet_started(players):
    return { 'type': NOT_YET_STARTED,
             'players': [{'name': p.name, 'started': p.started} for p in players] }
#             'players': dict((p.name, {'started': p.started}) for p in players) }

def in_progress(all_players, players_in_play,
           deal, artifacts, table, captured, pot, round_num, you=None):
    """
    Create a python object  with current game state, easily convertible to JSON.
    Generate the game status object.  If there is no `you`, it will
    not contain player-specific data.
    """

    moves = []
    for player in all_players:
        if player in deal.landos + deal.hans:
            move = 'decided'
        elif player in players_in_play:
            move = 'undecided'
        else:
            move = 'lando'

        moves.append({'name': player.name, 'move': move})

    obj = {
        'type' : IN_PROGRESS,
        'players' : moves,
        'table': [card.name for card in table],
        'captured': [card.name for card in captured],
        'pot': pot,
        'round': round_num,
        'artifacts': [artifact.name for artifact in artifacts]
        }

    if you:
        obj['you'] = you.name
        obj['loot'] = you.loot
        obj['artifacts'] = [artifact.name for artifact in you.artifacts]

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
        'players': [
            {'name': p.name,
             'loot': p.loot,
             'artifacts' : [artifact.name for artifact in p.artifacts] }
            for p in players ]
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
