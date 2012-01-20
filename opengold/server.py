#!/usr/bin/env python

import uuid
import json

from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.auth import authenticated, UserHandlingMixin

from db import Database

SESSION = 'session'

# support for longpolling
try:
    import gevent
    coro_lib = gevent
except:
    import eventlet
    coro_lib = eventlet

def game_name(func):
    """
    This decorator converts a game_name in the first argument to a game.
    """

    #def wrapped(self, game_name, *args):
    def wrapped(self, **kwargs):
        # game = self.db_conn.get_game(game_name)
        # func(self, game, *args)
        game = self.db_conn.get_game(kwargs['game_name'])
        func(self, game, **kwargs)

    return wrapped


class UserMixin(UserHandlingMixin):
    """
    Use this mixin to leverage Brubeck's UserHandlingMixin.
    """

    def get_current_user(self):
        """
        Return the user name associated with the cookie, or None
        if there is no cookie.
        """
        return self.get_cookie(SESSION, None, self.application.cookie_secret)


class StatusHandler(WebMessageHandler, UserMixin):

    @game_name
    @authenticated
    def get(self, game):
        """
        Get the status of a game, if it exists.
        """
        self.set_body(json.dumps(game.get_status(self.current_user))) # TODO: rendering!
        return self.render()


class StartHandler(WebMessageHandler, UserMixin):

    @game_name
    @authenticated
    def post(self, game):
        """
        Vote to start a game.  All players that have joined must agree
        to do this.
        """
        self.set_body(json.dumps(game.get_status(self.current_user))) # TODO: rendering!
        return self.render()


class ChatHandler(WebMessageHandler, UserMixin):

    @game_name
    @authenticated
    def post(self, game):
        """
        Message other players in the game.
        """
        self.get_param('message')
        self.set_body(json.dumps(game.get_status(self.current_user))) # TODO: rendering!
        return self.render()


class PollHandler(WebMessageHandler, UserMixin):

    @game_name
    @authenticated
    def post(self, game):
        """
        Poll for message to player.
        """
        if(self.current_user):
            while(True):
                msg = game.poll(self.current_user)
                if(msg):
                    break
                else:
                    coro_lib.sleep(0)

            self.set_body(json.dumps(msg))
        else:
            self.set_status(400, status_msg="You are not in this game.")

        return self.render()


class JoinHandler(WebMessageHandler):

    @game_name
    def post(self, game, **kwargs):
        """
        Try to join the game with the specified user name.  If it
        succeeds, feed the user a cookie!
        """
        player = kwargs['player']
        if game.add_player(player):
            # todo this will kill their involvement in other games.
            self.set_cookie(SESSION, player, self.application.cookie_secret)
            return self.render()

        self.set_status(400, status_msg="Could not join game.")
        return self.render()


class MoveHandler(WebMessageHandler, UserMixin):

    @authenticated
    @game_name
    def post(self, game, **kwargs):
        """
        Looks like we got a Lando!!
        """
        move = kwargs['move']
        if self.current_user:
            if game.submit_move(self.current_user, move):
                return self.render()

        return self.render(status_code=400)

        self.set_status(400, status_msg="Invalid move")
        return self.render()


config = {
    'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
    'handler_tuples': [(r'^/(?P<game_name>[^/]+)$', StatusHandler),
                       (r'^/(?P<game_name>[^/]+)/start$', StartHandler),
                       (r'^/(?P<game_name>[^/]+)/poll$', PollHandler),
                       (r'^/(?P<game_name>[^/]+)/join/(?P<player>[^/]+)$', JoinHandler),
                       (r'^/(?P<game_name>[^/]+)/move/(?P<move>lando|han)$', MoveHandler)],
    'cookie_secret': str(uuid.uuid4()),
    'db_conn': Database()
}


app = Brubeck(**config)
app.run()
