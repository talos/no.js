import json
import time

# REDIS KEYS
ROOMS = 'rooms'
USERS = 'users'
MESSAGES = 'messages'

# JSON KEYS
ID = 'id'
USER = 'user'
NAME = 'name'
MESSAGE = 'message'
TIME = 'time'

def path(key, *path):
    """
    Generate a path for redis.
    """
    return ':'.join([key] + list(path))

def join(r, room, user):
    """
    Join a room. Creates the room if it does not yet exist.

    Returns False if the user could not join, True otherwise.
    """

    # Create the room
    if r.sadd(path(ROOMS), room) == 1:
        r.publish(path(ROOMS), room)

    # Join the room
    if r.sadd(path(ROOMS, room, USERS), user) == 1:
        r.publish(path(ROOMS, room, USERS), user)
        return True
    else:
        return False

def message(r, room, user, message):
    """
    Broadcast chat message to all users. Garbage in, garbage out --
    make sure to protect against XSS outside of this.

    Returns True if the message was submitted, False otherwise.
    """
    if r.sismember(path(ROOMS, room, USERS), user):
        r.rpush(path(ROOMS, room, MESSAGES), json.dumps({
            USER: user,
            MESSAGE: message,
            TIME: time.strftime('%X') 
        }))
        r.publish(path(ROOMS, room, MESSAGES), room)
        return True
    else:
        return False

def users(r, room, id=-1):
    """
    Returns a generator that will yield a new ID and an array of users when the
    user list changes.
    """
    pubsub = r.pubsub()
    pubsub.subscribe(path(ROOMS, room, USERS))

    listener = pubsub.listen()

    while True:
        cur_id = r.llen(path(ROOMS, room, USERS))

        # Since user count varies up and down, check equality 
        if id != cur_id:
            listener.next()
        else:
            yield cur_id, [{ NAME: name } 
                           for name in r.lrange(path(ROOMS, room, USERS), 0, -1)]
            id = cur_id

def messages(r, room, id=-1, limit=50):
    """
    Returns a generator that will yield a new ID and an array of chat messages
    when a new message occurs.

    If the room doesn't exist, will initially yield a notice that the
    room doesn't exist.
    """
    pubsub = r.pubsub()
    pubsub.subscribe(path(ROOMS, room, MESSAGES))

    listener = pubsub.listen()

    while True:
        cur_id = r.llen(path(ROOMS, room, MESSAGES))

        # Block waiting for an update to generate something newer
        if id >= cur_id:
            listener.next()
        else:
            # Components are already in JSON.
            yield cur_id, [json.loads(j)
                           for j in r.lrange(path(ROOMS, room, MESSAGES),
                                             -limit,
                                             -1)]
            id = cur_id

def rooms(r, id=-1):
    """
    Returns a generator that will yield a new ID and an array of rooms when a
    new room appears.
    """
    pubsub = r.pubsub()
    pubsub.subscribe(path(ROOMS))

    listener = pubsub.listen()

    while True:
        cur_id = r.scard(path(ROOMS))

        # Block waiting for an update
        if id >= cur_id:
            listener.next()
        else:
            yield cur_id, [{ NAME: room,
                             USERS: r.scard(path(ROOMS, room, USERS)) }
                          for room in r.smembers(path(ROOMS))]
            id = cur_id
