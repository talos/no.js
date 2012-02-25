#!/usr/bin/env python

import redis
import chat 
from config import DB, COOKIE_SECRET, LONGPOLL_TIMEOUT, SEND_SPEC, RECV_SPEC 
from templating import load_mustache_env, MustacheRendering
from brubeck.request_handling import Brubeck, WebMessageHandler

try:
    import gevent.timeout.with_timeout as with_timeout
    import gevent.timeout.Timeout as Timeout
except ImportError:
    import eventlet.timeout.with_timeout as with_timeout
    import eventlet.timeout.Timeout as Timeout

#
# MIXINS
#
class UserMixin():

    def get_user(self, room):
        """
        Get the user for the specified room, or None if the
        user is not taking part.
        """
        return self.get_cookie(room, None, self.application.cookie_secret)


#
# HANDLERS
#
class IndexHandler(MustacheRendering):

    def get(self):
        """
        If the user wants to 'create' a room, forward them to it.

        Otherwise, list all rooms currently available.  Only returns if there
        is a room with an ID greater than the provided ID.
        """
        if self.get_argument('room'):
            return self.redirect('/%s/' % self.get_argument('room'))
        else:
            rooms = chat.rooms(self.db_conn,id=self.get_argument('id'))
            try:
                context = with_timeout(LONGPOLL_TIMEOUT, rooms.next)
                return self.render_template('index', **context)
            except Timeout:
                return self.redirect(self.message.path)


class RoomHandler(MustacheRendering):

    def get(self, room):
        """
        Render the room frameset (ew).
        """
        return self.render_template('room', **{'room': room})


class MessagesHandler(MustacheRendering):

    def get(self, room):
        """
        Render 'limit' messages for this room.  Should hang if there
        are no new messages.
        """
        messages = chat.messages(self.db_conn,
                                 room,
                                 limit=self.get_argument('limit'),
                                 id=self.get_argument('id'))

        try:
            context = with_timeout(LONGPOLL_TIMEOUT, messages.next)
            return self.render_template('messages', **context)
        except Timeout:
            return self.redirect(self.message.path)


class BufferHandler(MustacheRendering, UserMixin):
 
    def get(self, room):
        """
        Render the buffer for the user in their current room.

        This will either let them join the room, or say something.
        """
        return self.render_template('buffer',
                                    **{ 'room': room,
                                        'user': self.get_user(room) }

    def post(self, room):
        """
        Handle a post to the buffer form.  This should be a message if the
        user is in the chat, or a chat-join otherwise.
        """
        user = self.get_user(room)

        # If they're in the chat, they can send a message
        if user:
            message = self.get_argument('message')
            if chat.message(self.db_conn, room, user, message):
                self.set_status(204) # no reason to refresh the buffer
            else:
                self.set_status(400, "Could not send chat")
            return self.render()

        # Otherwise, they can join the chat
        else:
            user_name = self.get_argument('user')
            if chat.join(self.db_conn, room, user_name):
                # Only \w is allowed in room, so this is OK
                self.set_cookie(room, user_name, self.application.cookie_secret)
                return self.redirect(self.message.path)
            else:
                # TODO better rejection handling (common case for dupe names)
                self.set_status(400, "Could not add %s to room" % user_name)
                return self.render()


###
#
# RUN BRUBECK RUN
#
###
config = {
    'mongrel2_pair': (RECV_SPEC, SEND_SPEC),
    'handler_tuples': [(r'^/$', IndexHandler),
                       (r'^/(?P<room>\w+)/?$', RoomHandler),
                       (r'^/(?P<room>\w+)/buffer$', BufferHandler),
                       (r'^/(?P<room>\w+)/messages$', MessagesHandler)],
    'cookie_secret': COOKIE_SECRET,
    'db_conn': redis.StrictRedis(db=DB),
    'template_loader': load_mustache_env('./templates')
}

opengold = Brubeck(**config)
opengold.run()
