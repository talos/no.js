#!/usr/bin/env python

import redis
import chat 
import urllib2
from config import DB, COOKIE_SECRET, TIMEOUT, SEND_SPEC, RECV_SPEC 
from templating import load_mustache_env, MustacheRendering
from brubeck.request_handling import Brubeck 

try:
    import gevent as coro_lib
    import gevent.timeout as timeout
except ImportError:
    import eventlet as coro_lib
    import eventlet.timeout as timeout

TTL = TIMEOUT * 2

#
# MIXINS
#
class UserMixin():

    def get_user(self, room=None):
        """
        Get the user's current name, or None if they've never signed in or
        have an expired cookie.
        """
        name = self.get_cookie('name', None)
        secret = self.get_cookie('secret', None, self.application.cookie_secret)
        if name and secret and chat.validate(self.db_conn, name, secret):
            return name
        return None

    def register_user(self, name):
        """
        Register a user.  Returns True if the user was registered, False
        otherwise.
        """
        secret = chat.register(self.db_conn, name, ip=self.message.remote_addr)
        if secret:
            self.set_cookie('name', name)
            # encoded cookie, folks.  nothing to see here.
            self.set_cookie('secret', secret, self.application.cookie_secret)
            return True
        else:
            return False

class IdMixin():

    def get_id(self):
        """
        Get the ID from the arguments list, coerce it to an int if
        possible.  Otherwise, return None.
        """
        id = self.get_argument('id')
        try:
            return int(id) if id else None
        except ValueError:
            return None


#
# HANDLERS
#
class IndexHandler(MustacheRendering):

    def get(self):
        """
        Render the index frameset.  ew.
        """
        return self.render_template('index')


class RoomsHandler(MustacheRendering, IdMixin, UserMixin):

    def get(self):
        """
        List all rooms currently available.  Hangs until the number of rooms
        changes.

        This also works as a poll to keep a user in existence.
        """
        id = self.get_id()
        user = self.get_user()
        if user:
            chat.touch(self.db_conn, user, TTL)

        try:
            id, rooms = timeout.with_timeout(TIMEOUT, chat.rooms, self.db_conn, id)
            #self.headers['Refresh'] = refresh
            context = {
                'refresh': "0; url=?id=%d" % id, 
                'rooms': rooms
            }
            return self.render_template('rooms', **context)
        except timeout.Timeout:
            return self.redirect('?')

class BufferHandler(MustacheRendering, UserMixin):
 
    def _get_context(self):
        return { 'user': self.get_user(), 'room': self.get_argument('room')}

    def get(self):
        """
        Render the buffer for the user.
        """
        return self.render_template('buffer', **self._get_context())

    def post(self):
        """
        Handle a post to the buffer form.
        """
        context = self._get_context()
        register = self.get_argument('register')
        message = self.get_argument('message')
        join = self.get_argument('join')
        user = context['user']

        if register:
            if self.register_user(register):
                chat.touch(self.db_conn, register, TTL, context['room'])
                context['user'] = register
            else:
                context['error'] = "Name '%s' is taken." % register 
                # self.set_status(400, "Name '%s' is taken" % name)
        elif not user:
            context['error'] = 'You are no longer logged in.'
        elif message:
            if chat.message(self.db_conn, context['room'], user, message):
                #self.set_status(205) # 205 clears forms. Nobody supports it
                pass
            else:
                context['error'] = "Could not send message."
                # self.set_status(400, "Could not send message")
        # Joining a room changes the frameset and URL, so it requires redirect.
        elif join:
            return self.redirect('/%s/' % join)
        else:
            pass

        return self.render_template('buffer', **context)


class RoomHandler(MustacheRendering):

    def get(self, room):
        """
        Render the room frameset (ew).
        """
        room = urllib2.unquote(room)
        return self.render_template('room', **{'room': room})


class UsersHandler(MustacheRendering, UserMixin, IdMixin):

    def get(self, room):
        """
        Render the users currently in the room.  Hangs if nothing has happened
        since ID.

        This also functions as a poll for whether a user is still in a room.
        """
        room = urllib2.unquote(room)
        user = self.get_user()
        if user:
            chat.touch(self.db_conn, user, TTL, room)
        id = self.get_id()
        try:
            id, users = timeout.with_timeout(TIMEOUT, chat.users, self.db_conn, room, id=id)
            #self.headers['Refresh'] = refresh
            context = {
                'room': room,
                'users': users,
                'refresh': "0; url=?id=%d" % id 
            }
            return self.render_template('users', **context)
        except timeout.Timeout:
            return self.redirect('?')


class MessagesHandler(MustacheRendering, UserMixin, IdMixin):

    def get(self, room):
        """
        Render 'limit' messages for this room.  Should hang if there
        are no new messages.
        """
        room = urllib2.unquote(room)
        user = self.get_user()
        if user:
            chat.touch(self.db_conn, user, TTL, room)
        id = self.get_id()

        try:
            limit = int(self.get_argument('limit') or 25)
        except ValueError:
            limit = 25 

        try:
            id, messages = timeout.with_timeout(TIMEOUT,
                                                chat.messages,
                                                self.db_conn,
                                                room,
                                                limit=limit, id=id)
            context = {
                'refresh': "0; url=?id=%d#bottom" % id,
                'messages': messages,
                'room': room
            }
            return self.render_template('messages', **context)
            #self.headers['Refresh'] = refresh
        except timeout.Timeout:
            return self.redirect('?#bottom') 


def drain(db_conn):
    """
    Flush the database occasionally.
    """
    while True:
        chat.flush(db_conn)
        coro_lib.sleep(TIMEOUT) 

#
# RUN BRUBECK RUN
#
config = {
    'mongrel2_pair': (RECV_SPEC, SEND_SPEC),
    'handler_tuples': [(r'^/$', IndexHandler),
                       (r'^/rooms$', RoomsHandler),
                       (r'^/buffer$', BufferHandler),
                       (r'^/(?P<room>[^/]+)/?$', RoomHandler),
                       (r'^/(?P<room>[^/]+)/users$', UsersHandler),
                       (r'^/(?P<room>[^/]+)/messages$', MessagesHandler)],
    'cookie_secret': COOKIE_SECRET,
    'db_conn': redis.StrictRedis(db=DB),
    'template_loader': load_mustache_env('./templates')
}

opengold = Brubeck(**config)
toilet = opengold.pool.spawn(drain, opengold.db_conn)
opengold.run()
toilet.kill()
