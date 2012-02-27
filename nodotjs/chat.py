import json
import time
import uuid

# REDIS KEYS
ROOMS = 'rooms'
USERS = 'users'
MESSAGES = 'messages'
IP = 'ip'
TIMESTAMP = 'timestamp'
SECRET= 'secret'

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

def validate(r, user, secret):
    """
    Validate whether a user's secret is right.
    """
    if r.hget(path(USERS, user), SECRET) == secret:
        return True
    else:
        return False

def touch(r, user, ttl, room=None):
    """
    Indicate that a user is active, optionally in a room.
    """
    r.expire(path(USERS, user), ttl)
    if room:
        # If the room is new, send out a notification
        if r.sadd(path(ROOMS), room) == 1:
            _create_room(r, room)
        r.expire(path(ROOMS, room), ttl)

        # If the user is new, send out a notification
        if r.sadd(path(ROOMS, room, USERS), user) == 1:
            _join_room(r, room, user)
        r.expire(path(ROOMS, room, USERS, user), ttl)

def register(r, user, ip=None): # todo IP
    """
    Register a user.

    Returns a secret for the user if they can register, or None otherwise.
    """
    if r.exists(path(USERS, user)):
        return None
    else:
        secret = str(uuid.uuid4())
        _register_user(r, user, ip, secret)
        return secret

def message(r, room, user, message):
    """
    Broadcast chat message to all users. Garbage in, garbage out --
    make sure to protect against XSS outside of this.

    User 'None' is interpreted as a system message.

    Returns True if the message was submitted, False otherwise.
    """
    if (user is None) or r.exists(path(ROOMS, room, USERS, user)):
        p = path(ROOMS, room, MESSAGES)
        r.rpush(p, json.dumps({
            USER:    user,
            MESSAGE: message,
            TIME:    time.strftime('%X') 
        }))
        r.publish(p, room)
        return True
    else:
        return False

def rooms(r, id=None):
    """
    Returns a new ID and an array of rooms when the number of rooms changes.
    """
    # Block waiting for something to change
    p = path(ROOMS)
    if id == r.scard(p):
        pubsub = r.pubsub()
        pubsub.subscribe(p)
        pubsub.listen().next()
    # It's possible for the listener to break us out without changing ID
    return r.scard(p), [{ NAME: room,
                          USERS: r.scard(path(ROOMS, room, USERS)) }
                       for room in r.smembers(p)]

def users(r, room, id=None):
    """
    This returns a new ID and an array of users when the ID changes.
    """
    # Block waiting for something to change
    p = path(ROOMS, room, USERS)
    if id == r.scard(p):
        pubsub = r.pubsub()
        pubsub.subscribe(p)
        pubsub.listen().next()
    return r.scard(p), [{ NAME: name } for name in r.smembers(p)]

def messages(r, room, id=None, limit=25):
    """
    Returns a new ID and an array of messages when a new message occurs.

    Max of limit messages are returned.
    """
    # Block waiting for an update to generate something newer
    p = path(ROOMS, room, MESSAGES)
    if id == r.llen(p):
        pubsub = r.pubsub()
        pubsub.subscribe(p)
        pubsub.listen().next()
    # Components are already in JSON.
    return r.llen(p), [json.loads(j) for j in r.lrange(p, -limit, -1)]

def flush(r):
    """
    Chuck out expired users and rooms. This should be run at approximately
    the same interval as the timeout.
    """
    users = r.smembers(path(USERS))
    for user in users:
        if not r.exists(path(USERS, user)):
            _kill_user(r, user)

    rooms = r.smembers(path(ROOMS))
    for room in rooms:
        for user in r.smembers(path(ROOMS, room, USERS)):
            if not r.exists(path(ROOMS, room, USERS, user)):
                _leave_room(r, room, user)
        if r.scard(path(ROOMS, room, USERS)) == 0:
            _destroy_room(r, room)

def _create_room(r, room):
    r.hmset(path(ROOMS, room), { TIMESTAMP: time.time() } )
    r.publish(path(ROOMS), room)

def _destroy_room(r, room):
    p = path(ROOMS)
    r.srem(p, room)
    r.publish(p, room)

def _join_room(r, room, user):
    r.hmset(path(ROOMS, room, USERS, user), { TIMESTAMP: time.time() })
    r.publish(path(ROOMS, room, USERS), user)
    message(r, room, None, '%s has joined the room.' % user)

def _leave_room(r, room, user):
    p = path(ROOMS, room, USERS)
    r.srem(p, user)
    r.publish(p, user)
    message(r, room, None, '%s has left the room.' % user)

def _register_user(r, user, ip, secret):
    r.hmset(path(USERS, user), {IP: ip,
                                TIMESTAMP: time.time(),
                                SECRET: secret})
    p = path(USERS)
    r.sadd(p, user)
    r.publish(p, user)

def _kill_user(r, user):
    p = path(USERS)
    r.srem(p, user)
    r.publish(p, user)
