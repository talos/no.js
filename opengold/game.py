from deck import generate_deck, generate_artifacts, card_type
from redis import WatchError

import ast
import time
import random

MAX_ROUNDS = 5
ARTIFACT_VALUES = [5, 5, 10, 10, 15] # corresponding to which artifact this is

###
#
# Info keys
#
###
STATUS = 'status'
SPEAKER = 'speaker'
MESSAGE = 'message'
TIMESTAMP = 'timestamp'
JOINED = 'joined'
MOVED = 'moved'

VALUE = 'value'
PLAYER = 'player'
PLAYERS = 'players'
CARD = 'card'
DEATH = 'death'
VENTURING = 'venturing'

###
#
# Redis keys
#
###
CHAT = 'chat' # sorted set
UPDATE = 'update' # sorted set
ROUND = 'round' # integer

WAITING = 'waiting' #set
CAMP = 'camp' # set
LANDO = 'lando' # set
HAN = 'han' #set
CONFIRMED = 'confirmed' # set

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

LOCK = 'lock'

def path(key, *path):
    return ':'.join([key] + list(path))

def synchronized(func):
    """
    This decorator will cause the wrapped function to lock its key at
    the start, and unlock it at the end.  It also synchronizes,
    delaying execution until the lock can be obtained.
    """
    def wrapped(r, k, *args, **kwargs):
        pipe = r.pipeline()
        while True:
            try:
                pipe.watch(path(k, LOCK))
                if pipe.exists(path(k, LOCK)):
                    continue # TODO less optimism
                else:
                    pipe.multi()
                    pipe.set(path(k, LOCK), True)
                    pipe.execute()
                    retval = func(r, k, *args, **kwargs)
                    r.delete(path(k, LOCK))
                    return retval
            except WatchError:
                continue
            finally:
                pipe.reset()

    return wrapped

def chat(r, k, speaker, message):
    """
    Broadcast chat message to all players.
    """
    timestamp = time.time()

    r.zadd(path(k, CHAT), timestamp, {SPEAKER: speaker, MESSAGE: message})
    r.publish(k, CHAT)

def update(r, k, update):
    """
    Broadcast an update.
    """
    timestamp = time.time()
    r.zadd(path(k, UPDATE), timestamp, update)
    r.publish(k, UPDATE)

@synchronized
def get_info(r, k, start_time=0, player=None):
    """
    Check for status updates and chats since the specified start_time.
    If there were any status updates since the timestamp, the current
    status will be generated as well.  The presence of chats will not
    trigger the generation of a status object.  If there have been no
    chats or status updates since the timestamp, this will block until
    something happens.

    If start_time is unspecified, all messages will be pulled.  If
    player is unspecified, no player-specific data will be delivered.

    Returns a python object with an array of chats (if any), an array
    of updates (if any) a single status object (if there was an
    update), and a single player object (if a player was specified and
    there was an update).
    """

    now = time.time()
    pubsub = r.pubsub()
    pubsub.subscribe(k)

    while True:
        updates = [{ TIMESTAMP : entry[1],
                     UPDATE: ast.literal_eval(entry[0]) }
                   for entry in r.zrangebyscore(path(k, UPDATE),
                                                start_time,
                                                now,
                                                withscores=True)]
        chats = [{ TIMESTAMP : entry[1],
                   SPEAKER: ast.literal_eval(entry[0])[SPEAKER],
                   MESSAGE: ast.literal_eval(entry[0])[MESSAGE] }
                 for entry in r.zrangebyscore(path(k, CHAT),
                                              start_time,
                                              now,
                                              withscores=True)]
        if len(updates) + len(chats) == 0:
            pubsub.listen().next() # wait for an update
        else:
            break

    info = { TIMESTAMP : now }
    if len(chats) > 0:
        info[CHAT] = chats

    if len(updates) > 0:
        info[UPDATE] = updates
        info[STATUS] = {
            WAITING: list(r.smembers(path(k, WAITING))),
            CONFIRMED: list(r.smembers(path(k, CONFIRMED))),
            MOVED: list(r.sunion(path(k, LANDO), path(k, HAN))),
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
            elif r.sismember(path(k, CONFIRMED), player):
                decision = CONFIRMED
            elif r.sismember(path(k, LANDO), player):
                decision = LANDO
            elif r.sismember(path(k, HAN), player):
                decision = HAN
            info['you'] = {
                'name' : player,
                'decision' : decision,
                'loot' : r.hget(path(k, LOOT), player),
                'artifacts': r.lrange(path(k, ARTIFACTS_CAPTURED_PREFIX, player), 0, -1) }

    return info

@synchronized
def join(r, k, player):
    """
    Add a player to the waiting room.  Returns True if they have
    been added, or False otherwise.  Can only join this room if
    the game is not yet started.
    """
    if(r.exists(path(k, ROUND)) is False):
        if r.sadd(path(k, WAITING), player) == 1:
            update(r, k, {JOINED: player})
            return True
    return False

@synchronized
def confirm(r, k, player):
    """
    Player wants to start the next round.  If all players
    have done this, then the game advance to the round.  Returns
    True if the round has advanced, False otherwise.

    A single player cannot move the game from round 0 to round 1.
    """
    confirmed = r.smove(path(k, WAITING), path(k, CONFIRMED), player)
    if confirmed:
        update(r, k, { CONFIRMED: player })
    else:
        return False

    if(r.scard(path(k, WAITING)) == 0 and r.scard(path(k, CONFIRMED)) > 1):
        if not r.exists(path(k, ROUND)):  # game hasn't started yet
            r.rpush(path(k, DECK), *generate_deck())
            r.rpush(path(k, ARTIFACTS_UNSEEN), *generate_artifacts())
            #update(r, k, { CONFIRMED: list(r.smembers(r, k, CONFIRMED)) } )

        _round = r.incr(path(k, ROUND))
        new_artifact = r.rpop(path(k, ARTIFACTS_UNSEEN))
        update(r, k, { ROUND: _round } )
        update(r, k, { ARTIFACTS_IN_PLAY: new_artifact } )
        r.lpush(path(k, DECK), new_artifact)
        r.lpush(path(k, ARTIFACTS_IN_PLAY), new_artifact)
        return True

    return False

@synchronized
def move(r, k, player, move):
    """
    Submit a move for the specified player in the current round.
    Returns True if the move was submitted, False otherwise.
    """
    if move not in ['han', 'lando']:
        return False

    if r.smove(path(k, CONFIRMED), path(k, move), player):
        update(r, k, { MOVED: player } )
    else:
        return False

    if r.scard(path(k, CONFIRMED)) == 0:

        ####
        # LANDO LOVES LOOT
        ####
        if r.scard(path(k, LANDO)) > 0:
            landos = list(r.smembers(path(k, LANDO)))
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
                        update(r, k,
                               { ARTIFACTS_CAPTURED_PREFIX :
                                     { PLAYER : landos[0],
                                       CARD: card,
                                       VALUE: artifact_value } })
                        loot += artifact_value
                        r.rpush(path(k, ARTIFACTS_CAPTURED_PREFIX) + landos[0], card)
                    else:
                        update(r, k,
                               { ARTIFACTS_DESTROYED :
                                     { PLAYERS : landos,
                                       CARD: card,
                                       VALUE: artifact_value } })
                        r.rpush(path(k, ARTIFACTS_DESTROYED), card)

            remainder = loot % len(landos)
            payout = (loot - remainder) / len(landos)
            r.set(path(k, POT), remainder)
            r.sunionstore(path(k, CAMP), path(k, CAMP), path(k, LANDO))
            r.delete(path(k, LANDO))
            update(r, k, { CAPTURED : { PLAYERS : landos,
                                        VALUE : payout,
                                        POT: remainder }})
            for lando in landos:
                r.hincrby(path(k, LOOT), lando, payout)
        ####
        # END LOOTING
        ####

        ####
        # HANS VENTURE FORTH
        ####
        if r.scard(path(k, HAN)) > 0:
            hans = list(r.smembers(path(k, HAN)))
            card = r.lindex(path(k, DECK), random.randint(0, r.llen(path(k, DECK))))
            update(r, k, { CARD : card })

            # DEATH
            if card_type(card) == 'hazard' and card in r.lrange(path(k, TABLE), 0, -1):
                update(r, k, { DEATH : { PLAYERS: hans,
                                         CARD: card } })
                r.sunionstore(path(k, WAITING), path(k, HAN), path(k, CAMP))
                r.delete(path(k, CAMP))
            else:
                update(r, k, { VENTURING : hans } )
                r.sunionstore(path(k, CONFIRMED), path(k, HAN))
            r.delete(path(k, HAN))
            r.rpush(path(k, TABLE), r.lrem(path(k, DECK), 1, card))
        ####
        # END VENTURING
        ####

        if r.scard(path(k, CONFIRMED)) == 0:
            update(r, k, { WAITING: list(r.smembers(path(k, CAMP))) } )
            r.sunionstore(path(k, WAITING), path(k, CAMP))
            r.delete(path(k, CAMP))

    return True

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
