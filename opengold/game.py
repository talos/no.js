from deck import generate_deck, generate_artifacts, card_type

import ast
import time
import random
import itertools

MAX_ROUNDS = 5
ARTIFACT_VALUES = [5, 5, 10, 10, 15] # corresponding to which artifact this is

STATUS = 'status'
CHAT = 'chat'
UPDATE = 'update'

SPEAKER = 'speaker'
MESSAGE = 'message'
TIMESTAMP = 'timestamp'

ROUND = 'round' # integer

WAITING = 'waiting' #set
CAMP = 'camp' # set
LANDO = 'lando' # set
HAN = 'han' #set
UNDECIDED = 'undecided' # set

POT = 'pot' # integer
LOOT = 'loot' # hash by player name

DECK = 'deck' # list
TABLE = 'table' # list
CAPTURED = 'captured' # list
DESTROYED = 'destroyed' #list
ARTIFACTS_UNSEEN = 'artifacts.unseen' # list
ARTIFACTS_IN_PLAY = 'artifacts.in.play' # list
ARTIFACTS_CAPTURED_PREFIX = 'artifacts.captured' # prefix for lists
ARTIFACTS_DESTROYED = 'artifacts.destroyed' # list
ARTIFACTS_SEEN_COUNT = 'artifacts.seen.count' # integer

def path(key, *path):
    return ':'.join([key] + list(path))

def get_status(r, k, player=None):
    """
    Get the game's current status as a python object.
    Will include personal data if a player is specified.
    """
    state = {WAITING: list(r.smembers(path(k, WAITING))),
             UNDECIDED: list(r.smembers(path(k, UNDECIDED))),
             'decided': list(r.sunion(path(k, LANDO), path(k, HAN))),
             TABLE: r.lrange(path(k, TABLE), 0, -1),
             CAPTURED: r.lrange(path(k, CAPTURED), 0, -1),
             POT: r.get(path(k, POT)),
             ROUND: r.get(path(k, ROUND)),
             ARTIFACTS_DESTROYED: r.lrange(path(k, ARTIFACTS_DESTROYED), 0, -1),
             ARTIFACTS_SEEN_COUNT: r.get(path(k, ARTIFACTS_SEEN_COUNT)),
             ARTIFACTS_IN_PLAY: r.lrange(path(k, ARTIFACTS_IN_PLAY), 0, -1)}

    if player:
        if r.sismember(path(k, WAITING), player):
            decision = WAITING
        elif r.sismember(path(k, UNDECIDED), player):
            decision = UNDECIDED
        elif r.sismember(path(k, LANDO), player):
            decision = LANDO
        elif r.sismember(path(k, HAN), player):
            decision = HAN
        state['you'] = {
            'name' : player,
            'decision' : decision,
            'loot' : r.hget(path(k, LOOT), player),
            'artifacts': r.lrange(path(k, ARTIFACTS_CAPTURED_PREFIX, player), 0, -1) }

    return state

def get_chats(r, k, start_time, end_time=None):
    """
    Return a python array of chats between specified times.  end_time
    defaults to now.  The first chat is the oldest.
    """
    if end_time is None:
        end_time = time.time()
    return [{ TIMESTAMP : entry[1],
              SPEAKER: ast.literal_eval(entry[0])[SPEAKER],
              MESSAGE: ast.literal_eval(entry[0])[MESSAGE] }
            for entry in r.zrangebyscore(path(k, CHAT),
                                         start_time,
                                         end_time,
                                         withscores=True)]

def chat(r, k, speaker, message):
    """
    Broadcast chat message to all players.
    """
    timestamp = time.time()
    r.zadd(path(k, CHAT), timestamp, {SPEAKER: speaker, MESSAGE: message})
    r.publish(path(k), CHAT)

def get_updates(r, k, start_time, end_time=None):
    """
    Return a python array of updates between specified times.  end_time
    defaults to now.  The first update is the oldest.
    """
    if end_time is None:
        end_time = time.time()
    return [{ TIMESTAMP : entry[1],
              UPDATE: ast.literal_eval(entry[0]) }
            for entry in r.zrangebyscore(path(k, UPDATE),
                                         start_time,
                                         end_time,
                                         withscores=True)]

def update(r, k, update):
    """
    Broadcast an update.
    """
    timestamp = time.time()
    r.zadd(path(k, UPDATE), timestamp, {UPDATE: update})
    r.publish(path(k), UPDATE)

def join(r, k, player):
    """
    Add a player to the waiting room.  Returns True if they have
    been added, or False otherwise.  Can only join this room if
    the game is not yet started.
    """
    if(r.exists(path(k, ROUND)) is False):
        if r.sadd(path(k, WAITING), player) == 1:
            r.publish(path(k, STATUS), "%s joined the game." % player)
            return True
    return False

def confirm(r, k, player):
    """
    Player wants to start the next round.  If all players
    have done this, then the game advance to the round.  Returns
    True if the round has advanced, False otherwise.

    A single player cannot move the game from round 0 to round 1.
    """
    confirmed = r.smove(path(k, WAITING), path(k, UNDECIDED), player)
    if confirmed:
        r.publish(path(k, STATUS), "%s confirmed to move to move on to the next round.")
    else:
        return False

    if(r.scard(path(k, WAITING)) == 0 and r.scard(path(k, UNDECIDED)) > 1):
        if not r.exists(path(k, ROUND)):  # game hasn't started yet
            r.rpush(path(k, DECK), *generate_deck())
            r.rpush(path(k, ARTIFACTS_UNSEEN), *generate_artifacts())
            r.publish(path(k, STATUS), "Game started" )

        r.incr(path(k, ROUND))
        new_artifact = r.rpop(path(k, ARTIFACTS_UNSEEN))
        r.publish(path(k, STATUS), "Moving on to round %s: %s in play"
                  % (r.get(path, k, ROUND), new_artifact))
        r.lpush(path(k, DECK), new_artifact)
        r.lpush(path(k, ARTIFACTS_IN_PLAY), new_artifact)
        return True

    return False

def move(r, k, player, move):
    """
    Submit a move for the specified player in the current round.
    Returns True if the move was submitted, False otherwise.
    """
    if move not in ['han', 'lando']:
        return False

    if r.smove(path(k, UNDECIDED), path(k, move), player):
        r.publish(path(k, STATUS), "%s made a decision" % player)
    else:
        return False

    if r.scard(path(k, UNDECIDED)) == 0:
        r.publish(path(k, STATUS), "All players decided")

        ####
        # LANDO LOVES LOOT
        ####
        if r.scard(path(k, LANDO)) > 0:
            landos = r.smembers(path(k, LANDO))
            loot = r.get(path(k, POT)) or 0
            for card in r.lrange(path(k, TABLE), 0, -1):
                t = card_type(card)
                if t == 'treasure':
                    loot += card
                    r.lrem(path(k, TABLE), 1, card)
                    r.rpush(path(k, CAPTURED), card)
                    r.rpush(path(k, DECK), card)
                elif t == 'artifact':
                    r.lrem(path(k, TABLE), 1, card)
                    if len(landos) == 1: #  lucky lando
                        artifact_value = ARTIFACT_VALUES[r.get(path(k, ARTIFACTS_SEEN_COUNT)) or 0]
                        r.publish(path(k, STATUS), "Lando %s got lucky with %s, worth %s"
                                  % (landos[0], card, artifact_value))
                        loot += artifact_value
                        r.rpush(path(k, ARTIFACTS_CAPTURED_PREFIX) + landos[0], card)
                    else:
                        r.publish(path(k, STATUS), "Well %s was deestroyed" % card)
                        r.rpush(path(k, ARTIFACTS_DESTROYED), card)

            remainder = loot % len(landos)
            payout = (loot - remainder) / len(landos)
            r.set(path(k, POT), remainder)
            r.sunionstore(path(k, CAMP), path(k, CAMP), path(k, LANDO))
            r.delete(path(k, LANDO))
            r.publish(path(k, STATUS), "Landos %s made off with %s loot, leaving %s behind."
                      % (','.join(landos), payout, remainder))
            for lando in landos:
                r.hincrby(path(k, LOOT), lando, payout)
        ####
        # END LOOTING
        ####

        ####
        # HANS VENTURE FORTH
        ####
        if r.scard(path(k, HAN)) > 0:
            hans = r.smembers(path(k, HAN))
            r.publish(path(k, STATUS), "%s bravely forth" % (','.join(hans)))
            card = r.lindex(path(k, DECK), random.randint(0, r.llen(path(k, DECK))))
            r.publish(path(k, STATUS), "%s on the table" % card)

            # DEATH
            if card_type(card) == 'hazard' and card in r.lrange(path(k, TABLE), 0, -1):
                r.publish('%s killed %s. Confirm to start next round.'
                          % (card, ','.join(hans)))
                r.sunionstore(path(k, WAITING), path(k, HAN), path(k, CAMP))
                r.delete(path(k, CAMP))
            else:
                r.sunionstore(path(k, UNDECIDED), path(k, HAN))
            r.delete(path(k, HAN))
            r.rpush(path(k, TABLE), r.lrem(path(k, DECK), 1, card))
        ####
        # END VENTURING
        ####

        if r.scard(path(k, UNDECIDED)) == 0:
            r.publish("Wimps.  Confirm to start next round.")
            r.sunionstore(path(k, WAITING), path(k, CAMP))
            r.delete(path(k, CAMP))

    return True

def subscription(r, k, player=None):
    """
    Returns an iterable subscription for game events for the specified
    player, or generically if no player is specified.
    """

    # def msg_parse(m):
    #     if m['channel'] == path(k, STATUS):
    #         return { 'status': get_status(r, k, player),
    #                  'update': m['data'] }
    #     elif m['channel'] == path(k, CHAT):
    #         return { 'chats': get_chats(r, k, m['data'], m['data']) }

    pubsub = r.pubsub()
    pubsub.subscribe(
    # pubsub.subscribe([path(k, STATUS), path(k, CHAT)])
    # return itertools.imap(lambda m: m['data']
    #     itertools.ifilter(lambda m: m['type'] == 'message', pubsub.listen()) )

# def _determine_victors(self):
#     """
#     Return the players with the most points, breaking tie with
#     artifacts.  Ties only happen if there are identical points and
#     artifacts.
#     """
#     by_loot = {}
#     for player in self._players:
#         loot = player.loot
#         by_loot[loot] = by_loot.get(loot, []) + [player]

#     most_loot = sorted(by_loot.keys(), reverse=True)[0]
#     candidates = by_loot[most_loot]

#     by_artifacts = {}
#     for candidate in candidates:
#         artifacts = len(candidate.artifacts)
#         by_artifacts[artifacts] = by_artifacts.get(artifacts, []) + [candidate]
#     most_artifacts = sorted(by_artifacts.keys(), reverse=True)[0]

#     return by_artifacts[most_artifacts]
