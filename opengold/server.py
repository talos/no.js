#!/usr/bin/env python

import uuid
import redis
import json
import sys
import urllib2

import game
from templating import load_mustache_env, MustacheRendering

from brubeck.request_handling import Brubeck, WebMessageHandler


def unquote_game_name(func):
    """
    Replace the decorated function's first argument with an unquoted
    version of the game_name.
    """
    def wrapped(self, game_name, *args, **kwargs):
        func(self, urllib2.unquote(game_name), *args, **kwargs)
    return wrapped

def redirect_unless_json(func):
    """
    Redirect to the game unless the request was for JSON.
    """

    def wrapped(self, game_name, *args, **kwargs):
        game_name = urllib2.unquote(game_name)
        func(self, game_name, *args, **kwargs)

        if self.message.content_type == 'application/json':
            self.headers['Content-Type'] = 'application/json'
            self.set_body(json.dumps(context))
            return self.render()
        else:
            return self.render_template('app', **context)

    return wrapped


class PlayerMixin():
    """
    This mixin provides a get_player() method.  The passed game_name
    should already be unquoted, as it will be re-quoted.
    """
    def get_player(self, game_name):
        """
        Get the player for the specified game_name, or None if the
        user is not taking part.  game_name should not be quoted.
        """
        return self.get_cookie(urllib2.quote(game_name, ''), None, self.application.cookie_secret)


class IndexHandler(MustacheRendering):

    def get(self):
        """
        List all games currently available.
        """

        context = {'names': game.list_names(self.db_conn)}
        if self.message.content_type == 'application/json':
            self.headers['Content-Type'] = 'application/json'
            self.set_body(json.dumps(context))
            return self.render()
        else:
            return self.render_template('app', **context)


class CreateGameHandler():

    def get(self):
        """
        'Create' a game -- really just forward directly to a game page.
        """
        if self.get_argument('name'):
            return self.redirect(self.get_argument('name') + '/')
        else:
            return self.redirect('/')


class ForwardToGameHandler(WebMessageHandler):

    def get(self, game_name):
        """
        Games should be accessed with a trailing slash.
        """
        return self.redirect(game_name + '/')

class GameHandler(MustacheRendering, PlayerMixin):

    @unquote_game_name
    def get(self, game_name):
        """
        Get information about happenings in game since id.  Will
        block until something happens after id.  ID defaults to 0.
        """
        start_id = self.get_argument('id') or 0

        info = game.info(self.db_conn, game_name, self.get_player(game_name), start_id)
        context = info.next()

        if self.message.content_type == 'application/json':
            self.headers['Content-Type'] = 'application/json'
            self.set_body(json.dumps(context))
            return self.render()
        else:
            return self.render_template('app', **context)

class ChatHandler(MustacheRendering, PlayerMixin):

    @redirect_unless_json
    @unquote_game_name
    def post(self, game_name):
        """
        Message other players in the game.
        """
        message = self.get_argument('message')
        player = self.get_player(game_name)

        if message and player:
            if game.chat(self.db_conn, game_name, player, message):
                return 200
            else:
                return 400, "Could not send chat"
        elif player is None:
            return 400, "You are not in this game"
        else:
            return 400, "You did not specify a message body"


class JoinHandler(WebMessageHandler, PlayerMixin):

    def post(self):
        """
        Try to join the game with the post-specified player name `player`.
        If it succeeds, feed the user a cookie!
        """
        game_name = self.get_argument('game')

        if self.get_player(game_name):  # player already in this game
            return 400, "You are already in this game"
        elif self.get_argument('player'):
            player_name = self.get_argument('player')
            if game.join(self.db_conn, game_name, player_name):
                self.set_cookie(urllib2.quote(game_name, ''), player_name, self.application.cookie_secret)
                return 200
            else:
                return 400, "Could not add %s to game" % player_name
        else:
            return 400, "You must specify a name to join"


class StartHandler(WebMessageHandler, PlayerMixin):

    @redirect_unless_json
    @unquote_game_name
    def post(self, game_name):
        """
        Vote to enter temple/advance to next round.
        """
        player = self.get_player(game_name)
        if player:
            game.start(self.db_conn, game_name, player)
            return 200
        else:
            return 400, 'You are not in this game'


class MoveHandler(WebMessageHandler, PlayerMixin):

    @redirect_unless_json
    @unquote_game_name
    def post(self, game_name):
        """
        Looks like we got a Lando!!
        """
        player = self.get_player(game_name)
        if player:
            if game.move(self.db_conn, game_name, player, self.get_argument('move')):
                return 200
            else:
                return 400, 'Could not submit move'
        else:
            return 400, 'You are not in this game'


config = {
    'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
    'handler_tuples': [(r'^/$', IndexHandler),
                       (r'^/join$', JoinHandler),
                       (r'^/create$', CreateGameHandler),
                       (r'^/(?P<game_name>[^/]+)$', ForwardToGameHandler),
                       (r'^/(?P<game_name>[^/]+)/$', GameHandler),
                       (r'^/(?P<game_name>[^/]+)/start$', StartHandler),
                       (r'^/(?P<game_name>[^/]+)/move$', MoveHandler)],
    'cookie_secret': str(uuid.uuid4()),  # this will kill all sessions/games if the server crashes!
    'db_conn': redis.StrictRedis(db=sys.argv[1] if len(sys.argv) > 1 else 'opengold'),
    'template_loader': load_mustache_env('templates')
}


opengold = Brubeck(**config)
opengold.run()
