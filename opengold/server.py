#!/usr/bin/env python

import uuid

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

    def wrapped(self, game_name, *args):
        game = self.db_conn.get_game(game_name)
        func(self, game, *args)

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


class StatusHandler(WebMessageHandler):

    @game_name
    @authenticated
    def get(self, game):
        """
        Get the status of a game, if it exists.
        """
        self.set_body(game.get_status(self.current_user)) # TODO: rendering!
        return self.render()


class PollHandler(WebMessageHandler):

    @game_name
    def post(self, game):
        """
        Poll for advancement of game status.  Resolves when the game
        status has changed.
        """
        last_state_id = game.state_id
        while last_state_id == game.state_id:
            coro_lib.sleep(0)

        return self.render()


class JoinHandler(WebMessageHandler):

    @game_name
    def post(self, game, player):
        """
        Try to join the game with the specified user name.  If it
        succeeds, feed the user a cookie!
        """

        if game.add_player(player):
            # todo this will kill their involvement in other games.
            self.set_cookie(SESSION, player, self.application.cookie_secret)
            return self.render()

        self.set_status(400, "Could not join game.")
        return self.render()


class MoveHandler(WebMessageHandler):

    @authenticated
    @game_name
    def post(self, game, move):
        """
        Looks like we got a Lando!!
        """
        if self.current_user:
            if game.submit_move(self.current_user, move):
                return self.render()

        return self.render(status_code=400)

        self.set_status(400, status_msg="Invalid move")
        return self.render()


config = {
    'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
    'handler_tuples': [(r'^(?P<game_name>[^/]+)$', StatusHandler),
                       (r'^(?P<game_name>[^/]+)/poll$', PollHandler),
                       (r'^(?P<game_name>[^/]+)/join/(?P<player>[^/]+)$', JoinHandler),
                       (r'^(?P<game_name>[^/]+)/(?P<move>lando|han)$', MoveHandler)],
    'cookie_secret': str(uuid.uuid4()),
    'db_conn': Database()
}


app = Brubeck(**config)
app.run()
