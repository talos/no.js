#!/usr/bin/env python

import uuid
import redis
import json

import game

from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.templating import load_jinja2_env, Jinja2Rendering


class PlayerMixin():
    """
    This mixin provides a player method.
    """

    def get_player(self, game_name):
        """
        Get the player for the specified game_name, or None if the
        user is not taking part.
        """
        return self.get_cookie(game_name, None, self.application.cookie_secret)


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

    def get(self):
        return self.render_template('app.html')


class InfoHandler(WebMessageHandler, PlayerMixin):

    def get(self, game_name, start_id):
        """
        Get information about happenings in game since start_id.  Will
        block until something happens after start_id.
        """
        info = game.get_info(self.db_conn, game_name, self.get_player(game_name), start_id)
        self.set_body(info) # TODO: rendering!
        return self.render()

class ChatHandler(WebMessageHandler):

    def post(self, game_name):
        """
        Message other players in the game.
        """
        message = self.get_param('message')
        player = self.get_player(game_name)
        if message and player:
            game.chat(self.db_conn, game_name, player, message)
            self.set_status(200)
            #self.redirect('/%s' % kwargs['game_name'])
        elif player is None:
            self.set_status(400, status_msg="You are not in this game")
        elif message is None:
            self.set_status(400, status_msg="You did not specify a message body")
        else:
            self.set_status(400)

        return self.render()


class ConfirmHandler(WebMessageHandler, PlayerMixin):

    def post(self, game_name):
        """
        Vote to advance to the next round.
        """
        player = self.get_player(game_name)
        if player:
            game.confirm(self.db_conn, game_name, player)
            self.set_status(200)
            #self.redirect('/%s' % kwargs['game_name'])
        else:
            self.set_status(400, status_msg="You are not in this game")

        return self.render()

class JoinHandler(WebMessageHandler, PlayerMixin):

    def post(self, game_name):
        """
        Try to join the game with the post-specified player name `player`.
        If it succeeds, feed the user a cookie!
        """
        if self.get_player(game_name):  # they are already logged in
            self.set_status(400, status_msg="You are already in this game")
        elif self.get_argument('player'):
            player_name = self.get_argument('player')
            if game.join(self.db_conn, game_name, player_name):
                self.set_cookie(game_name, player_name, self.application.cookie_secret)
                self.set_status(200)
                #self.redirect('/%s' % kwargs['game_name'])
            else:
                self.set_status(400, status_msg="Could not add %s to game" % player_name)
        else:
            self.set_status(400, status_msg="You must specify a name to join.")

        return self.render()


class MoveHandler(WebMessageHandler, PlayerMixin):

    def post(self, game_name):
        """
        Looks like we got a Lando!!
        """
        player = self.get_player(game_name)
        if player:
            if game.move(self.db_conn, game_name, player, self.get_argument('move')):
                self.set_status(200)
                #self.redirect('/%s' % kwargs['game_name'])
            else:
                self.set_status(400, status_msg="Could not submit move.")
        else:
            self.set_status(400, status_msg="You are not in this game.")
        return self.render()


config = {
    'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
    'handler_tuples': [(r'^/$', IndexHandler),
                       (r'^/(?P<game_name>[^/]+)$', GameHandler),
                       (r'^/(?P<game_name>[^/]+)/status/(?P<start_id>\d+)$', InfoHandler),
                       (r'^/(?P<game_name>[^/]+)/join$', JoinHandler),
                       (r'^/(?P<game_name>[^/]+)/confirm$', ConfirmHandler),
                       (r'^/(?P<game_name>[^/]+)/move$', MoveHandler)],
                       #(r'^/(?P<game_name>[^/]+)/poll$', PollHandler)],
    'cookie_secret': str(uuid.uuid4()),  # this will kill all sessions/games if the server crashes!
    'db_conn': redis.StrictRedis(),
    'template_loader': load_jinja2_env('templates')
}


app = Brubeck(**config)
app.run()
