#!/usr/bin/env python

import uuid
import json

from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.templating import load_jinja2_env, Jinja2Rendering

from db import Database
from message import NOT_YET_STARTED, IN_PROGRESS

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


class IndexHandler(Jinja2Rendering):

    def get(self):
        """
        List all games currently available.
        """
        if self.get_argument('game'):
            return self.redirect(self.get_argument('game'))
        else:
            context = {
                'games': [{ 'name': name,
                            'status': self.db_conn.get_game(name).get_status() }
                          for name in self.db_conn.get_all_names()]
                }
            return self.render_template('index.html', **context)

class GameHandler(Jinja2Rendering):

    @game
    def get(self, game, player, *args, **kwargs):
        status = game.get_status(player)
        context = {
            'game_name': kwargs['game_name'],
            'status' : status
            }
        s = status['type']
        if s is NOT_YET_STARTED and player is None:
            return self.render_template('join.html', **context)
        elif s is NOT_YET_STARTED:
            return self.render_template('start.html', **context)
        elif s is IN_PROGRESS:
            return self.render_template('in_progress.html', **context)
        else:
            return self.render_template('finished.html', **context)


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
            self.redirect('/%s' % kwargs['game_name'])
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
            self.redirect('/%s' % kwargs['game_name'])
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
        Try to join the game with the post-specified player name `player`.
        If it succeeds, feed the user a cookie!
        """
        if player:  # they are already logged in
            self.set_status(400, status_msg="You are already in this game as %s" % player)
        elif self.get_argument('player'):
            player_name = self.get_argument('player')
            if game.add_player(player_name):
                self.set_cookie(kwargs['game_name'], player_name, self.application.cookie_secret)
                self.redirect('/%s' % kwargs['game_name'])
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
        if player:
            if game.submit(player, self.get_argument('move')):
                self.redirect('/%s' % kwargs['game_name'])
            else:
                self.set_status(400, status_msg="Could not submit move.")
        else:
            self.set_status(400, status_msg="You are not in this game.")
        return self.render()


config = {
    'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
    'handler_tuples': [(r'^/$', IndexHandler),
                       (r'^/(?P<game_name>[^/]+)$', GameHandler),
                       (r'^/(?P<game_name>[^/]+)/status$', StatusHandler),
                       (r'^/(?P<game_name>[^/]+)/start$', StartHandler),
                       (r'^/(?P<game_name>[^/]+)/poll$', PollHandler),
                       (r'^/(?P<game_name>[^/]+)/join$', JoinHandler),
                       (r'^/(?P<game_name>[^/]+)/move$', MoveHandler)],
    'cookie_secret': str(uuid.uuid4()),  # this will kill all sessions/games if the server crashes!
    'db_conn': Database(),
    'template_loader': load_jinja2_env('templates')
}


app = Brubeck(**config)
app.run()
