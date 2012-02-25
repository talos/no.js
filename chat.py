def path(key, *path):
    """
    Generate a path for redis.
    """
    return ':'.join([key] + list(path))

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
        _publish_update(r, k)
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

        # Block waiting for an update to generate something newer
        if start_info_id >= cur_id:
            if start_info_id == -1:
                start_info_id = 0
                yield { NAME: k,
                        GAME: { NOT_EXISTS: True },
                        UPDATE_ID: start_info_id }
            listener.next()
        else:
            # Components are already in JSON.
            info = {
                NAME: k,
                UPDATES:
                    [json.loads(j) for j in r.lrange(path(k, UPDATES), 0, num_updates)],
                ID: cur_id }

            if r.exists(path(k, SAVED)):
                info[GAME] = json.loads(r.lindex(path(k, SAVED), -1))

            if player:
                saved_player = r.lindex(path(k, PLAYERS, player, SAVED), -1)
                if saved_player:
                    info[YOU] = json.loads(saved_player)

            yield info
            start_info_id = cur_id

def rooms(r, id=0):
    """
    Returns a generator that will yield an object with an array of rooms
    in 'rooms', and an id under 'id'.
    """
    pubsub = r.pubsub()
    pubsub.subscribe(ROOMS)

    listener = pubsub.listen()

    while True:
        cur_id = int(r.get(ROOM_ID) or -1)

        # Block waiting for an update
        if id >= cur_id:
            if id == -1:
                id = 0
                yield { GAMES: [],
                        ID: id }
            listener.next()
        else:
            yield { ID: id,
                    GAMES: [{
                        NAME: k,
                        ROUND: r.get(path(k, ROUND)),
                        PLAYERS: r.scard(path(k, PLAYERS))
                        }
                            for k in r.zrevrange(GAMES, 0, -1)] }
            start_game_id = cur_id
