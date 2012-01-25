from deck import TREASURES, HAZARDS, ARTIFACTS, Treasure, Hazard, Artifact, get_card
from redis import WatchError

import ast
import time

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
YOU = 'you'
NAME = 'name'

VALUE = 'value'
PLAYERS = 'players'
CARD = 'card'
DEATH = 'death'
CHAT = 'chat'
UPDATE = 'update'

# Locations
L_CAMP = 'camp'
L_TEMPLE = 'temple'

# Decisions
D_LANDO = 'lando'
D_HAN = 'han'

###
#
# Redis keys
#
###
INFO_ID = 'id' # integer
INFO = 'info' # list

ROUND = 'round' # integer

PLAYERS = 'players' # set
DECISION = 'decision' # key in hash
LOCATION = 'location' # key in hash
LOOT = 'loot' # key in hash
ARTIFACTS_CAPTURED = 'artifacts.captured' # list prefixed by PLAYERS:player

POT = 'pot' # integer

DECK = 'deck' # set
TABLE = 'table' # list
CAPTURED = 'captured' # list
ARTIFACTS_UNSEEN = 'artifacts.unseen' # set
ARTIFACTS_IN_PLAY = 'artifacts.in.play' # set
ARTIFACTS_DESTROYED = 'artifacts.destroyed' # set
ARTIFACTS_SEEN_COUNT = 'artifacts.seen.count' # integer

LOCK = 'lock'

def timestamp():
    """
    Convenience method that returns milliseconds since the UNIX epoch.
    """
    return int(time.time() * 1000)

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

def chat(r, k, speaker, message, superuser=False):
    """
    Broadcast chat message to all players.  Garbage in, garbage out --
    make sure to protect against XSS outside of this.  By default,
    only players in the game are allowed to speak.  Pass True to
    superuser to override this.

    Returns True if the message was submitted, False otherwise.
    """
    if r.sismember(path(k, PLAYERS), speaker) or superuser:
        r.rpush(path(k, INFO), { CHAT:
               { SPEAKER: speaker,
                 MESSAGE: message,
                 INFO_ID: r.incr(path(k, INFO_ID)),
                 TIMESTAMP: timestamp() }})
        r.publish(k, CHAT)
        return True
    else:
        return False

def _get_players(r, k):
    """
    Get a list of all players in the game.
    """
    return [r.hgetall(path(k, PLAYERS, name))
            for name in sorted(r.smembers(path(k, PLAYERS)))]

def _update(r, k, update):
    """
    Broadcast an update.  This should not be called externally.  The
    update must be a dict.
    """
    update[TIMESTAMP] = timestamp()
    update[INFO_ID] = r.incr(path(k, INFO_ID))
    r.rpush(path(k, INFO), { UPDATE: update })
    r.publish(k, UPDATE)

def _deal_card(r, k):
    """
    Deal a single card.  Should only be called from already
    synchronized function internally.

    A single card is moved from a random point in the deck onto the
    right side of the table.

    The dealt card, not its index, is returned.
    """
    card_idx = r.spop(path(k, DECK))
    r.rpush(path(k, TABLE), card_idx)
    card = get_card(card_idx)
    _update(r, k, { CARD : card.name })

    if isinstance(card, Artifact):
        artifacts_seen_count = r.incr(path(k, ARTIFACTS_SEEN_COUNT))
        _update(r, k, { ARTIFACTS_SEEN_COUNT: int(artifacts_seen_count) })

    return card

def get_info(r, k, player=None, start_id=0, signal={}):
    """
    Calls generate_info if there has been activity since start_id,
    which defaults to 0.  If there has not been activity, blocks until
    there is.

    If signal is passed, making 'stop' in signal Truthy will terminate
    this call.
    """
    pubsub = r.pubsub()
    pubsub.subscribe(k)
    listener = pubsub.listen()

    while True:
        if start_id >= int(r.get(path(k, INFO_ID)) or 0):
            listener.next() # wait for an update
            continue
        elif 'stop' in signal:
            break
        else:
            break

    return generate_info(r, k, player, start_id)

@synchronized
def generate_info(r, k, player=None, start_id=0):
    """
    Check for status updates and chats since the specified start_id,
    inclusive.  If there were any status updates since the id, the
    current status will be generated as well.  The presence of chats
    will not trigger the generation of a status object.

    If start_id is unspecified, all messages will be pulled.  If
    player is unspecified, no player-specific data will be delivered.

    Returns a python object with an array of chats (if any), an array
    of updates (if any), a single status object (if there was an
    update), and a single player object (if a player was specified and
    there was an update).
    """
    all_info = [ast.literal_eval(entry) for entry in r.lrange(path(k, INFO), start_id, -1)]
    chats = [i[CHAT] for i in filter(lambda i: CHAT in i, all_info)]
    updates = [i[UPDATE] for i in filter(lambda i: UPDATE in i, all_info)]

    info = { INFO_ID: int(r.get(path(k, INFO_ID)) or 0) }
    if len(chats) > 0:
        info[CHAT] = chats

    if len(updates) > 0:
        info[UPDATE] = updates
        players = _get_players(r, k)
        info[STATUS] = {
            PLAYERS: [{NAME: p[NAME],
                       LOCATION: p[LOCATION],
                       DECISION: DECISION in p }  # only show True/False
                      for p in players],
            TABLE: [get_card(idx).name for idx in r.lrange(path(k, TABLE), 0, -1)],
            CAPTURED: [get_card(idx).name for idx in r.lrange(path(k, CAPTURED), 0, -1)],
            POT: int(r.get(path(k, POT)) or 0),
            ROUND: int(r.get(path(k, ROUND)) or 0),
            ARTIFACTS_DESTROYED: [get_card(idx).name for idx in r.lrange(path(k, ARTIFACTS_DESTROYED), 0, -1)],
            ARTIFACTS_SEEN_COUNT: int(r.get(path(k, ARTIFACTS_SEEN_COUNT)) or 0),
            ARTIFACTS_IN_PLAY: [get_card(idx).name for idx in r.lrange(path(k, ARTIFACTS_IN_PLAY), 0, -1)]}

        if player:
            info[YOU] = next((p for p in players if p[NAME] == player), None)

    return info

@synchronized
def join(r, k, player):
    """
    Add a player to the waiting room.  Returns True if they have
    been added, or False otherwise.  Can only join this room if
    the game is not yet started.

    Garbage in, garbage out -- make sure to protect against XSS
    (player name) outside of this.
    """
    if r.exists(path(k, ROUND)) is False:
        if r.sadd(path(k, PLAYERS), player) == 1:
            r.hmset(path(k, PLAYERS, player), { NAME: player,
                                                LOCATION: L_CAMP })
            _update(r, k, {L_CAMP: player})
            return True
    return False

@synchronized
def enter_temple(r, k, player):
    """
    Player wants to enter the temple.  They can only do this if the
    table is clear and they are not already inside.  Returns True if
    they entered.

    This will start the game when everyone is in the temple, but a
    single player can't move the game from round 0 to round 1.
    """
    if (r.hget(path(k, PLAYERS, player), LOCATION) == L_CAMP and
        not r.exists(path(k, TABLE))):
        r.hset(path(k, PLAYERS, player), LOCATION, L_TEMPLE)
        _update(r, k, { L_TEMPLE: player } )
    else:
        return False

    players = _get_players(r, k)

    if(all(map(lambda p: p[LOCATION] == L_TEMPLE, players)) and
       len(players) > 1):
        # game hasn't started yet
        if not r.exists(path(k, ROUND)):
            r.sadd(path(k, DECK), *TREASURES)
            r.sadd(path(k, DECK), *HAZARDS)
            r.sadd(path(k, ARTIFACTS_UNSEEN), *ARTIFACTS)
        else:
            # push everything on the table and captured back into the deck
            return_to_deck = r.lrange(path(k, TABLE), 0, -1) + r.lrange(path(k, CAPTURED), 0, -1)
            if len(return_to_deck):
                r.sadd(path(k, DECK), *return_to_deck)
            r.delete(path(k, TABLE), path(k, DECK))

        _round = r.incr(path(k, ROUND))
        new_artifact = r.spop(path(k, ARTIFACTS_UNSEEN))
        _update(r, k, { ROUND: int(_round) } )
        _update(r, k, { ARTIFACTS_IN_PLAY: get_card(new_artifact).name } )
        r.sadd(path(k, DECK), new_artifact)
        r.rpush(path(k, ARTIFACTS_IN_PLAY), new_artifact)

        _deal_card(r, k)

    return True

@synchronized
def move(r, k, player, move):
    """
    Submit a move for the specified player in the current round.
    Returns True if the move was submitted, False otherwise.
    """
    if move not in [D_HAN, D_LANDO]:
        return False

    if (r.hget(path(k, PLAYERS, player), LOCATION) == L_TEMPLE
        and not r.hexists(path(k, PLAYERS, player), DECISION)):
        r.hset(path(k, PLAYERS, player), DECISION, move)
        _update(r, k, { DECISION: player } )
    else:
        return False

    players = _get_players(r, k)
    if all(map(lambda p: DECISION in p,
               filter(lambda p: p[LOCATION] == L_TEMPLE, players))):

        ####
        # LANDO LOVES LOOT
        ####
        landos = map(lambda p: p[NAME], filter(lambda p: p[DECISION] == D_LANDO, players))
        if len(landos) > 0:
            loot = r.get(path(k, POT)) or 0
            for card_idx in r.lrange(path(k, TABLE), 0, -1):
                card = get_card(card_idx)
                if isinstance(card, Treasure):
                    loot += card.value
                    r.lrem(path(k, TABLE), 1, card_idx)
                    r.rpush(path(k, CAPTURED), card_idx)
                    #r.rpush(path(k, DECK), card)
                elif isinstance(card, Artifact):
                    r.lrem(path(k, TABLE), 1, card_idx)
                    if len(landos) == 1: #  lucky lando
                        artifact_value = ARTIFACT_VALUES[int(r.get(path(k, ARTIFACTS_SEEN_COUNT)) or 0)]
                        _update(r, k,
                               { ARTIFACTS_CAPTURED :
                                     { PLAYERS : landos[0],
                                       CARD: card,
                                       VALUE: artifact_value } })
                        loot += artifact_value
                        r.rpush(path(k, PLAYERS, landos[0], ARTIFACTS_CAPTURED), card_idx)
                    else:
                        _update(r, k,
                               { ARTIFACTS_DESTROYED :
                                     { PLAYERS : landos,
                                       CARD: card,
                                       VALUE: artifact_value } })
                        r.rpush(path(k, ARTIFACTS_DESTROYED), card_idx)

            remainder = loot % len(landos)
            payout = (loot - remainder) / len(landos)
            r.set(path(k, POT), remainder)

            for lando in landos:
                r.hset(path(k, PLAYERS, lando), LOCATION, L_CAMP)
                r.hincrby(path(k, PLAYERS, lando), LOOT, payout)

            _update(r, k, { CAPTURED : { PLAYERS : landos,
                                         VALUE : payout,
                                         POT: remainder }})
        ####
        # END LOOTING
        ####

        ####
        # HANS VENTURE FORTH
        ####
        hans = map(lambda p: p[NAME], filter(lambda p: p[DECISION] == D_HAN, players))
        if len(hans) > 0:
            card = _deal_card(r, k)

            # DEATH -- outta the temple
            if (isinstance(card, Hazard) and
                card.name in [get_card(idx).name
                              for idx in r.lrange(path(k, TABLE), 0, -2)]):
                _update(r, k, { DEATH : { PLAYERS: hans,
                                          CARD: card.name } })
                for han in hans:
                    r.hset(path(k, PLAYERS, han), LOCATION, L_CAMP)
                hans = []
            else:
                _update(r, k, { L_TEMPLE : hans } )
        ####
        # END VENTURING
        ####

        for player in players:
            r.hdel(path(k, PLAYERS, player[NAME]), DECISION)

        if len(hans) == 0:
            r.delete(path(k, TABLE))

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
