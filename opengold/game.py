from deck import TREASURES, HAZARDS, ARTIFACTS, Treasure, Hazard, Artifact, get_card
from redis import WatchError

import ast
import time

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
CARD = 'card'
DEATH = 'death'
CHAT = 'chat'
UPDATE = 'update'

# States
LANDO = 'lando'  # T/L
HAN = 'han'      # T/H
UNDECIDED = 'undecided'  # T/X
CAMP = 'camp'  # C/X
MOVED = 'moved'

###
#
# Redis keys
#
###
GAMES = 'games' # set

INFO_ID = 'id' # integer
INFO = 'info' # list

ROUND = 'round' # integer

PLAYERS = 'players' # set
STATE = 'state' # key in hash
LOOT = 'loot' # key in hash
ARTIFACTS_CAPTURED = 'artifacts.captured' # list prefixed by PLAYERS:player
DONE = 'done'

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
                r.delete(path(k, LOCK)) # when it's not Can, Deadlock is bad
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
        info_id = r.incr(path(k, INFO_ID))
        r.rpush(path(k, INFO), { CHAT:
               { SPEAKER: speaker,
                 MESSAGE: message,
                 INFO_ID: info_id,
                 TIMESTAMP: timestamp() }})
        r.publish(k, info_id)
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
    info_id = r.incr(path(k, INFO_ID))
    update[TIMESTAMP] = timestamp()
    update[INFO_ID] = info_id
    r.rpush(path(k, INFO), { UPDATE: update })
    r.publish(k, info_id)

def _deal_card(r, k):
    """
    Deal a single card.  Should only be called from already
    synchronized function internally.

    A single card is moved from a random point in the deck onto the
    right side of the table.

    Returns True if the card meant death, False otherwise.
    """

    table_card_names = [get_card(idx).name for idx in r.lrange(path(k, TABLE), 0, -1)]
    card_idx = r.spop(path(k, DECK))

    r.rpush(path(k, TABLE), card_idx)
    card = get_card(card_idx)
    _update(r, k, { CARD : card.name })

    if isinstance(card, Artifact):
        artifacts_seen_count = r.incr(path(k, ARTIFACTS_SEEN_COUNT))
        _update(r, k, { ARTIFACTS_SEEN_COUNT: int(artifacts_seen_count) })
        return False
    elif isinstance(card, Hazard) and card.name in table_card_names:
        return True
    else:
        return False

def list_names(r):
    """
    List all game names. GARBAGE IN GARBAGE OUT! Make sure to sanitize
    output as appropriate.
    """
    return sorted(list(r.smembers(GAMES)))

def info(r, k, player=None, start_id=0):
    """
    Returns a generator that will return info objects newer than the
    last one it generated, starting with start_id.

    The generator will return None once if there is nothing newer or
    the game doesn't exist.  A subsequent call to .next() will block
    until something newer becomes available.
    """
    pubsub = r.pubsub()
    pubsub.subscribe(k)

    listener = pubsub.listen()

    while True:
        if start_id >= int(r.get(path(k, INFO_ID)) or 0):
            yield None
            listener.next() # block waiting for an update to
                            # generate something newer
        else:
            info = generate_info(r, k, player, start_id)
            start_id = info[INFO_ID]
            yield info

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
                       STATE: p[STATE] if p[STATE] in [UNDECIDED, CAMP] else MOVED }  # redacted
                      for p in players],
            TABLE: [get_card(idx).name for idx in r.lrange(path(k, TABLE), 0, -1)],
            CAPTURED: [get_card(idx).name for idx in r.lrange(path(k, CAPTURED), 0, -1)],
            POT: int(r.get(path(k, POT)) or 0),
            ROUND: r.get(path(k, ROUND)),
            ARTIFACTS_DESTROYED: [get_card(idx).name for idx in r.lrange(path(k, ARTIFACTS_DESTROYED), 0, -1)],
            ARTIFACTS_SEEN_COUNT: int(r.get(path(k, ARTIFACTS_SEEN_COUNT)) or 0),
            ARTIFACTS_IN_PLAY: [get_card(idx).name for idx in r.lrange(path(k, ARTIFACTS_IN_PLAY), 0, -1)]}

        if player:
            you = next((p for p in players if p[NAME] == player), None)
            you[ARTIFACTS_CAPTURED] = [get_card(idx).name for idx in r.lrange(path(k, PLAYERS, player, ARTIFACTS_CAPTURED), 0, -1)]
            you[LOOT] = int(you.get(LOOT, 0))
            info[YOU] = you

    return info

def _next_round(r, k):
    """
    Deal a card and an artifact.
    """
    new_artifact = r.spop(path(k, ARTIFACTS_UNSEEN))
    assert new_artifact is not None
    _round = r.incr(path(k, ROUND))
    _update(r, k, { ROUND: int(_round) } )
    _update(r, k, { ARTIFACTS_IN_PLAY: get_card(new_artifact).name } )
    assert r.sadd(path(k, DECK), new_artifact) == 1
    r.rpush(path(k, ARTIFACTS_IN_PLAY), new_artifact)
    _deal_card(r, k)

def _advance_game_state(r, k):
    """
    # GAME STATE MACHINE
    #
    # None => 1      :: more than 1 player, no players are UNDECIDED.  Create game.
                        Deal a card and an artifact.
    # r    => r + 1  :: there are artifacts left, but all players in CAMP.
                        Clear the table,
                        Deal a card and an artifact card and Push all players to UNDECIDED.
    # r    => 'done' :: there are no artifacts left
    """
    players = _get_players(r, k)

    if(not r.exists(path(k, ROUND)) and
       not any(p[STATE] == UNDECIDED for p in players) and
       len(players)):
        r.sadd(path(k, DECK), *TREASURES)
        r.sadd(path(k, DECK), *HAZARDS)
        r.sadd(path(k, ARTIFACTS_UNSEEN), *ARTIFACTS)
        _next_round(r, k)
    elif r.scard(path(k, ARTIFACTS_UNSEEN)) and all(p[STATE] == CAMP for p in players):
        # push everything on the table and captured back into the deck
        return_to_deck = r.lrange(path(k, TABLE), 0, -1) + r.lrange(path(k, CAPTURED), 0, -1)
        if len(return_to_deck):
            r.sadd(path(k, DECK), *return_to_deck)
            r.delete(path(k, TABLE), path(k, CAPTURED))

        for player in players:
            r.hset(path(k, PLAYERS, player), STATE, UNDECIDED)

        _next_round()
    elif not r.exists(path(k, ARTIFACTS_UNSEEN)) and r.get(path(k, ROUND)) != DONE:
        r.set(path(k, ROUND), DONE)
        _update(r, k, { DONE: True })

def _advance_player_state(r, k):
    """
    han   => undecided | camp
    lando => camp

    This will cause another card to be dealt if at least one player is
    in HAN state.
    """
    players = _get_players(r, k)
    if not any(p[STATE] == UNDECIDED for p in players):

        ####
        # LANDO LOVES LOOT
        ####
        landos = filter(lambda p: p[STATE] == LANDO, players)
        if len(landos) > 0:
            loot = int(r.get(path(k, POT)) or 0)
            for card_idx in r.lrange(path(k, TABLE), 0, -1):
                card = get_card(card_idx)
                if isinstance(card, Treasure):
                    loot += card.value
                    r.lrem(path(k, TABLE), 1, card_idx)
                    r.rpush(path(k, CAPTURED), card_idx)
                elif isinstance(card, Artifact):
                    r.lrem(path(k, TABLE), 1, card_idx)
                    artifact_value = ARTIFACT_VALUES[int(r.get(path(k, ARTIFACTS_SEEN_COUNT)) or 0)]
                    r.lrem(path(k, ARTIFACTS_IN_PLAY), 1, card_idx)
                    if len(landos) == 1: #  lucky lando
                        _update(r, k,
                                { ARTIFACTS_CAPTURED :
                                      { PLAYERS : landos[0][NAME],
                                        CARD: card.name,
                                        VALUE: artifact_value } })
                        loot += artifact_value
                        r.rpush(path(k, PLAYERS, landos[0][NAME], ARTIFACTS_CAPTURED), card_idx)
                    else:
                        _update(r, k,
                               { ARTIFACTS_DESTROYED :
                                     { PLAYERS : sorted([l[NAME] for l in landos]),
                                       CARD: card.name,
                                       VALUE: artifact_value } })
                        r.rpush(path(k, ARTIFACTS_DESTROYED), card_idx)

            remainder = loot % len(landos)
            payout = (loot - remainder) / len(landos)
            r.set(path(k, POT), remainder)

            for lando in landos:
                r.hset(path(k, PLAYERS, lando[NAME]), STATE, CAMP) # LANDO => CAMP
                r.hincrby(path(k, PLAYERS, lando[NAME]), LOOT, payout)

            _update(r, k, { CAPTURED : { PLAYERS : sorted([l[NAME] for l in landos]),
                                         VALUE : payout,
                                         POT: remainder }})
        ####
        # END LOOTING
        ####

        ####
        # HANS VENTURE FORTH
        ####
        hans = filter(lambda p: p[STATE] == HAN, players)
        if len(hans) > 0:
            death = _deal_card(r, k)

            names = sorted([h[NAME] for h in hans])
            if death:
                _update(r, k, { DEATH : { PLAYERS: names,
                                          CARD: card.name } })
            else:
                _update(r, k, { HAN : names } )

            for han in hans:
                r.hset(path(k, PLAYERS, han[NAME]), STATE, CAMP if death else UNDECIDED)
        ####
        # END VENTURING
        ####

@synchronized
def move(r, k, player, move):
    """
    UNDECIDED => HAN | LANDO

    Submit a move for the specified player in the current round.
    Returns True if the move was submitted, False otherwise.

    A player can only move if the move is HAN or LANDO and they are
    UNDECIDED.
    """
    if move in (HAN, LANDO) and r.hget(path(k, PLAYERS, player), STATE) == UNDECIDED:
        r.hset(path(k, PLAYERS, player), STATE, move)
        _update(r, k, { MOVED: player } )
        _advance_game_state(r, k)
        _advance_player_state(r, k)
        return True
    else:
        return False

@synchronized
def join(r, k, player):
    """
    nil => UNDECIDED

    Move a player from nowhere into the UNDECIDED state.  This is only
    possible if they are not in the game, and the game is not yet
    started.  Returns true if the player was added, false otherwise.

    Garbage in, garbage out -- make sure to protect against XSS
    (player name) outside of this.
    """

    if not r.sismember(path(k, PLAYERS), player) and not r.exists(path(k, ROUND)):
        r.sadd(GAMES, k)
        r.sadd(path(k, GAMES), k)
        assert r.sadd(path(k, PLAYERS), player) == 1
        r.hmset(path(k, PLAYERS, player), { NAME: player,
                                            STATE: UNDECIDED })
        _update(r, k, {CAMP: player})
        return True
    return False

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
