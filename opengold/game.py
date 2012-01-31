from deck import TREASURES, HAZARDS, ARTIFACTS, Treasure, Hazard, Artifact, get_card
from redis import WatchError
import json
import time

ARTIFACT_VALUES = [5, 5, 10, 10, 15] # Value corresponding to which artifact this is.  Beware of the 0-index.

# Player states
JOINED = 'joined'
CAMP = 'camp'
UNDECIDED = 'undecided'
LANDO = 'lando'
HAN = 'han'
WON = 'won'
LOST = 'lost'

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
MORE_PLAYERS = "more_players"

VALUE = 'value'
CARD = 'card'
DEATH = 'death'
CHAT = 'chat'

MOVED = 'moved'
NOT_EXISTS = 'not_exists'

ID = 'id'

###
#
# Redis keys
#
###
GAMES = 'games' # sorted set
GAME_ID = 'game_id' # integer

UPDATE_ID = 'id' # integer
SAVED = 'saved' # list
UPDATES = 'updates' # list

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
UNLOCKED = 'unlocked'
LOCKED = 'locked'

def timestamp():
    """
    Convenience method that returns milliseconds since the UNIX epoch.
    """
    return int(time.time() * 1000)

def path(key, *path):
    return ':'.join([key] + list(path))

def advances_game_state(func):
    """
    This decorator will wraps functions called with (r, k, player,
    *args) to lock a game's key at the start. If the wrapped function
    returned True, it will be published as an update, and then
    _advance_game_state will be called.  Returns True if there was an
    update, False otherwise. Always unlocks game at end.

    It also synchronizes, delaying execution until the lock can be
    obtained.
    """
    def wrapped(r, k, player, *args):
        pipe = r.pipeline()
        while True:
            try:
                pipe.watch(path(k, LOCK))
                if pipe.get(path(k, LOCK)) == LOCKED:
                    #pubsub = pipe.pubsub()
                    #pubsub.subscribe(path(k, LOCK))
                    #pubsub.listen().next()
                    continue # TODO less optimism -- pubsub?
                else:
                    pipe.multi()
                    pipe.set(path(k, LOCK), LOCKED)
                    pipe.execute()

                    try:
                        if func(r, k, player, *args):
                            _save_update(r, k, { func.func_name: player })
                            _advance_game_state(r, k)
                            _save_game_state(r, k)
                            _publish_info(r, k)
                            return True
                        else:
                            return False
                    finally:
                        r.set(path(k, LOCK), UNLOCKED) # when it's not Can, Deadlock is bad
            except WatchError:
                continue
            finally:
                pipe.reset()
                #r.publish(path(k, LOCK), '')

    return wrapped

def _get_players(r, k):
    """
    Get a list of all players in the game formed as dictionaries.
    Notates them with their artifacts.
    """
    players = [r.hgetall(path(k, PLAYERS, name))
               for name in sorted(r.smembers(path(k, PLAYERS)))]

    for player in players:
        player[player[STATE]] = True  # a bit hacky, but this makes templating easier
        player[ARTIFACTS_CAPTURED] = [
            get_card(idx).name
            for idx in r.lrange(path(k, PLAYERS, player[NAME], ARTIFACTS_CAPTURED), 0, -1)]

    return players

def _publish_info(r, k):
    """
    Notify .info() that there is new information.
    """
    r.publish(k, r.get(path(k, UPDATE_ID)))

def _save_update(r, k, update):
    """
    Save an update as json.  This should not be called externally.
    The update must be a dict, and will be merged with TIMESTAMP and
    UPDATE_ID keys.

    It is pushed onto the left of the list.
    """
    update_id = r.incr(path(k, UPDATE_ID))
    update[TIMESTAMP] = timestamp()
    update[UPDATE_ID] = update_id
    r.lpush(path(k, UPDATES), json.dumps(update))

def _save_game_state(r, k):
    """
    Saves a JSON representation of the game's current state.
    """
    players = _get_players(r, k)

    for player in players:
        r.rpush(path(k, PLAYERS, player[NAME], SAVED), json.dumps(player))

    game_state = {
        PLAYERS:
            [ p if p[STATE] in [WON, LOST] else
              { NAME: p[NAME],
                STATE: MOVED if p[STATE] in [HAN, LANDO] else p[STATE] }
              for p in players],
        TABLE:
            [get_card(idx).name for idx in r.lrange(path(k, TABLE), 0, -1)],
        CAPTURED:
            [get_card(idx).name for idx in r.lrange(path(k, CAPTURED), 0, -1)],
        POT: int(r.get(path(k, POT)) or 0),
        ARTIFACTS_DESTROYED:
            [get_card(idx).name for idx in r.lrange(path(k, ARTIFACTS_DESTROYED), 0, -1)],
        ARTIFACTS_SEEN_COUNT: int(r.get(path(k, ARTIFACTS_SEEN_COUNT)) or 0),
        ARTIFACTS_IN_PLAY:
            [get_card(idx).name for idx in r.lrange(path(k, ARTIFACTS_IN_PLAY), 0, -1)]
        }

    if r.exists(path(k, ROUND)):
        game_state[ROUND] = r.get(path(k, ROUND))

    r.rpush(path(k, SAVED), json.dumps(game_state))

def _advance_game_state(r, k):
    """
    GAME STATE MACHINE

    ALL LOGIZ HURR
    """
    if not r.zscore(GAMES, k):
        _initialize_game(r, k)

    players = _get_players(r, k)
    if len(players) < 2:
        if players[0][STATE] == CAMP:
            _save_update(r, k, {MORE_PLAYERS: True})
    elif r.get(path(k, ROUND)) == DONE:
        pass
    elif any(p[STATE] == JOINED for p in players):
        pass
    elif all(p[STATE] == CAMP for p in players):
        if int(r.scard(path(k, ARTIFACTS_UNSEEN))) > 0:
            _next_round(r, k, players) # CAMP => UNDECIDED
        else:
            _game_over(r, k, players) # CAMP => WON | LOST
    elif not any(p[STATE] == UNDECIDED for p in players):
        landos = filter(lambda p: p[STATE] == LANDO, players)
        hans = filter(lambda p: p[STATE] == HAN, players)
        assert len(landos) + len(hans) > 0
        if len(landos):
            _take_loot(r, k, landos)  # LANDO => CAMP
        if len(hans):  # HAN => CAMP | UNDECIDED
            _deal_card(r, k, hans)
        _advance_game_state(r, k)

def _initialize_game(r, k):
    """
    Create deck, artifacts etc.
    """
    game_id = r.incr(GAME_ID)
    assert r.zadd(GAMES, game_id, k) == 1

    r.delete(path(k, DECK))
    r.delete(path(k, ARTIFACTS_UNSEEN))

    r.sadd(path(k, DECK), *TREASURES)
    r.sadd(path(k, DECK), *HAZARDS)
    r.sadd(path(k, ARTIFACTS_UNSEEN), *ARTIFACTS)

    r.publish(GAMES, game_id)

def _next_round(r, k, players):
    """
    PLAYER:: CAMP => UNDECIDED

    Clear the table, move everyone from CAMP to UNDECIDED, and deal an
    artifact and a card.
    """
    # push everything on the table and captured back into the deck
    return_to_deck = r.lrange(path(k, TABLE), 0, -1) + r.lrange(path(k, CAPTURED), 0, -1)
    if len(return_to_deck):
        r.sadd(path(k, DECK), *return_to_deck)
        r.delete(path(k, TABLE), path(k, CAPTURED))

    for player in players:
        r.hset(path(k, PLAYERS, player[NAME]), STATE, UNDECIDED)

    new_artifact = r.spop(path(k, ARTIFACTS_UNSEEN))
    _round = r.incr(path(k, ROUND))
    _save_update(r, k, { ROUND: int(_round) } )
    _save_update(r, k, { ARTIFACTS_IN_PLAY: get_card(new_artifact).name } )
    assert r.sadd(path(k, DECK), new_artifact) == 1
    r.rpush(path(k, ARTIFACTS_IN_PLAY), new_artifact)
    _deal_card(r, k)

def _take_loot(r, k, landos):
    """
    PLAYER:: LANDO => CAMP

    This will move all Landos back to CAMP, giving them loot.
    """
    loot = int(r.get(path(k, POT)) or 0)
    for card_idx in r.lrange(path(k, TABLE), 0, -1):
        card = get_card(card_idx)
        if isinstance(card, Treasure):
            loot += card.value
            r.lrem(path(k, TABLE), 1, card_idx)
            r.rpush(path(k, CAPTURED), card_idx)
        elif isinstance(card, Artifact):
            r.lrem(path(k, TABLE), 1, card_idx)
            artifact_value = ARTIFACT_VALUES[int(r.get(path(k, ARTIFACTS_SEEN_COUNT))) - 1]
            r.lrem(path(k, ARTIFACTS_IN_PLAY), 1, card_idx)
            if len(landos) == 1: #  lucky lando
                _save_update(r, k,
                             { ARTIFACTS_CAPTURED :
                                   { PLAYERS : landos[0][NAME],
                                     CARD: card.name,
                                     VALUE: artifact_value } })
                loot += artifact_value
                r.rpush(path(k, PLAYERS, landos[0][NAME], ARTIFACTS_CAPTURED), card_idx)
            else:
                _save_update(r, k,
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

    _save_update(r, k, { LANDO : { PLAYERS : sorted([l[NAME] for l in landos]),
                                      VALUE : payout,
                                      POT: remainder }})

def _deal_card(r, k, hans=[]):
    """
    PLAYER:: HAN => UNDECIDED | CAMP

    This will deal another card and push any hans either back to camp
    (death) or back to undecided.

    A single card is moved from a random point in the deck onto the
    right side of the table.
    """
    prior_card_names = [get_card(idx).name for idx in r.lrange(path(k, TABLE), 0, -1)]
    card_idx = r.spop(path(k, DECK))

    r.rpush(path(k, TABLE), card_idx)
    card = get_card(card_idx)
    _save_update(r, k, { CARD : card.name })

    if isinstance(card, Hazard) and card.name in prior_card_names:
        _save_update(r, k, { DEATH : { PLAYERS: sorted([h[NAME] for h in hans]),
                                  CARD: card.name } })
        new_state = CAMP
    else:
        new_state = UNDECIDED
        if hans:
            _save_update(r, k, { HAN : { PLAYERS : sorted([h[NAME] for h in hans])}})
        if isinstance(card, Artifact):
            artifacts_seen_count = r.incr(path(k, ARTIFACTS_SEEN_COUNT))
            _save_update(r, k, { ARTIFACTS_SEEN_COUNT: int(artifacts_seen_count) })

    for han in hans:
        r.hset(path(k, PLAYERS, han[NAME]), STATE, new_state)


def _game_over(r, k, players):
    """
    PLAYER:: CAMP => WON | LOST

    The players with the most points wins, breaking ties with
    artifacts.  Ties only happen if there are identical points and
    artifacts.  Unfiltered status is published.
    """
    by_loot = {}

    for player in players:
        loot = player[LOOT]
        by_loot[loot] = by_loot.get(loot, []) + [player]

    most_loot = sorted(by_loot.keys(), reverse=True)[0]
    candidates = by_loot[most_loot]

    by_artifacts = {}
    for candidate in candidates:
        artifacts = player[ARTIFACTS_CAPTURED]
        by_artifacts[len(artifacts)] = by_artifacts.get(len(artifacts), []) + [candidate]

    most_artifacts = sorted(by_artifacts.keys(), reverse=True)[0]
    winners = by_artifacts[most_artifacts]
    for player in players:
        r.hset(path(k, PLAYERS, player[NAME]), STATE, WON if player in winners else LOST)

    r.set(path(k, ROUND), DONE)
    _save_update(r, k, { ROUND: DONE,
                         PLAYERS: _get_players(r, k) })

@advances_game_state
def join(r, k, player):
    """
    PLAYER:: nil => JOINED

    Move a player from nowhere into the JOINED state.  This is only
    possible if they are not in the game, and the game still has no
    Round.

    Garbage in, garbage out -- make sure to protect against XSS
    (player name) outside of this.
    """

    if(not r.sismember(path(k, PLAYERS), player) and
       not r.exists(path(k, ROUND))):
        assert r.sadd(path(k, PLAYERS), player) == 1
        r.hmset(path(k, PLAYERS, player), { NAME: player,
                                            STATE: JOINED })
        return True
    else:
        return False

@advances_game_state
def start(r, k, player):
    """
    PLAYER:: JOINED => CAMP

    Move a player from the JOINED to the CAMP state.  This is only
    possible if they were in the JOINED state.
    """
    if r.hget(path(k, PLAYERS, player), STATE) == JOINED:
        r.hset(path(k, PLAYERS, player), STATE, CAMP)
        return True
    else:
        return False

@advances_game_state
def move(r, k, player, move):
    """
    UNDECIDED => HAN | LANDO

    Submit a move for the specified player in the current round.

    A player can only move if the move is HAN or LANDO and they are
    UNDECIDED.
    """
    if move in (HAN, LANDO) and r.hget(path(k, PLAYERS, player), STATE) == UNDECIDED:
        r.hset(path(k, PLAYERS, player), STATE, move)
        return True
    else:
        return False

def chat(r, k, speaker, message, superuser=False):
    """
    Broadcast chat message to all players.  Garbage in, garbage out --
    make sure to protect against XSS outside of this.  By default,
    only players in the game are allowed to speak.  Pass True to
    superuser to override this.

    Returns True if the message was submitted, False otherwise.
    """
    if r.sismember(path(k, PLAYERS), speaker) or superuser:
        _save_update(r, k, { CHAT: { SPEAKER: speaker,
                                     MESSAGE: message }})
        return True
    else:
        return False

def info(r, k, player=None, start_info_id=-1, num_updates=10):
    """
    Returns a generator that will return info objects newer than the
    last one it generated, starting with start_info_id.

    If the game doesn't exist, will initially yield a notice that the
    game doesn't exist.
    """
    pubsub = r.pubsub()
    pubsub.subscribe(k)

    listener = pubsub.listen()

    while True:
        cur_id = int(r.get(path(k, UPDATE_ID)) or -1)
        # Game doesn't exist yet.
        if cur_id == -1 and start_info_id == -1:
            yield { STATE: { NOT_EXISTS: True },
                    UPDATE_ID: 0 }
            start_info_id = 0
        # Block waiting for an update to generate something newer
        elif start_info_id >= cur_id:
            listener.next()
        else:
            # Components are already in JSON.
            info = {
                UPDATES:
                    [json.loads(j) for j in r.lrange(path(k, UPDATES), 0, num_updates)],
                ID: cur_id }

            if r.exists(path(k, SAVED)):
                info[STATE] = json.loads(r.lindex(path(k, SAVED), -1))

            if player:
                saved_player = r.lindex(path(k, PLAYERS, player, SAVED), -1)
                if saved_player:
                    info[YOU] = json.loads(saved_player)

            start_info_id = cur_id
            yield info

def games(r, start_game_id=-1):
    """
    Returns a generator that will return an object containing a list
    of all games every time a new one is created, starting with the
    specified start_game_id.  Games are ordered most recent first.

    GARBAGE IN GARBAGE OUT for names! Make sure to sanitize output as
    appropriate.
    """
    pubsub = r.pubsub()
    pubsub.subscribe(GAMES)

    listener = pubsub.listen()

    while True:
        cur_id = int(r.get(GAME_ID) or -1)

        # no games t'all
        if cur_id == -1 and start_game_id == -1:
            yield { GAMES: [],
                    UPDATE_ID: 0 }
            start_game_id = 0
        # Block waiting for an update
        elif start_game_id >= cur_id:
            listener.next()
        else:
            yield { ID: cur_id,
                    GAMES: [{
                        NAME: k,
                        ROUND: r.get(path(k, ROUND)),
                        PLAYERS: r.scard(path(k, PLAYERS))
                        }
                            for k in r.zrevrange(GAMES, 0, -1)] }
            start_game_id = cur_id
