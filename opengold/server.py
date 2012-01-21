#!/usr/bin/env python

import uuid
import json

from brubeck.request_handling import Brubeck, WebMessageHandler

from db import Database

# support for longpolling
try:
    import gevent
    coro_lib = gevent
except:
    import eventlet
    coro_lib = eventlet

def game(func):
    """
    This decorator converts a game_name in the first argument to a
    game.  It also passes a player_name argument, which is None if the
    user is not logged into that game.
    """

    def wrapped(self, *args, **kwargs):
        game_name = kwargs['game_name']
        game = self.db_conn.get_game(game_name)
        player = self.get_cookie(game_name, None, self.application.cookie_secret)
        return func(self, game, player, *args, **kwargs)

    return wrapped


class StatusHandler(WebMessageHandler):

    @game
    def get(self, game, player, *args, **kwargs):
        """
        Get the status of a game.
        """
        status = json.dumps(game.get_status(player))
        self.set_body(status) # TODO: rendering!
        return self.render()


class StartHandler(WebMessageHandler):

    @game
    def post(self, game, player, *args, **kwargs):
        """
        Vote to start a game.  All players that have joined must agree
        to do this.
        """
        if player:
            game.start(player)  # perhaps suboptimal -- returns 200
                                # whether the game started or not, but
                                # we want to be able to confirm via
                                # status that the user was even in a
                                # position to vote on this.
            self.set_status(200)
        else:
            self.set_status(400, status_msg="You are not in this game")

        return self.render()


class ChatHandler(WebMessageHandler):

    @game
    def post(self, game, player, *args, **kwargs):
        """
        Message other players in the game.
        """
        message = self.get_param('message')
        if message and player:
            game.chat(player, message)
            self.set_status(200)
        elif player is None:
            self.set_status(400, status_msg="You are not in this game")
        elif message is None:
            self.set_status(400, status_msg="You did not specify a message body")
        else:
            self.set_status(400)

        return self.render()


class PollHandler(WebMessageHandler):

    @game
    def post(self, game, player, *args, **kwargs):
        """
        Poll for message to player.
        """
        if player:
            while(True):
                msg = game.poll(player)
                if(msg):
                    break
                else:
                    coro_lib.sleep(0)

            self.set_body(json.dumps(msg))
        else:
            self.set_status(400, status_msg="You are not in this game.")

        return self.render()


class JoinHandler(WebMessageHandler):

    @game
    def post(self, game, player, *args, **kwargs):
        """
        Try to join the game with the specified user name.  If it
        succeeds, feed the user a cookie!
        """
        if player:  # they are already logged in
            self.set_status(400, status_msg="You are already in this game as %s" % player)
        elif 'player_name' in kwargs:
            player_name = kwargs['player_name']
            if game.add_player(player_name):
                self.set_cookie(kwargs['game_name'], player_name, self.application.cookie_secret)
                self.set_status(200)
            else:
                self.set_status(400, status_msg="Could not add %s to game" % player_name)
        else:
            self.set_status(400, status_msg="You must specify a name to join.")

        return self.render()


class MoveHandler(WebMessageHandler):

    @game
    def post(self, game, player, *args, **kwargs):
        """
        Looks like we got a Lando!!
        """
        move = kwargs['move']
        if player:
            if game.submit(player, move):
                self.set_status(200)
            else:
                self.set_status(400, status_msg="Could not submit move.")
        else:
            self.set_status(400, status_msg="You are not in this game.")
        return self.render()


config = {
    'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
    'handler_tuples': [(r'^/(?P<game_name>[^/]+)$', StatusHandler),
                       (r'^/(?P<game_name>[^/]+)/start$', StartHandler),
                       (r'^/(?P<game_name>[^/]+)/poll$', PollHandler),
                       (r'^/(?P<game_name>[^/]+)/join/(?P<player_name>[^/]+)$', JoinHandler),
                       (r'^/(?P<game_name>[^/]+)/move/(?P<move>lando|han)$', MoveHandler)],
    'cookie_secret': str(uuid.uuid4()),  # this will kill all sessions/games if the server crashes!
    'db_conn': Database()
}


app = Brubeck(**config)
app.run()
