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
        return func(self, urllib2.unquote(game_name), *args, **kwargs)
    return wrapped

def redirect_unless_json(func):
    """
    If this request was for json, this returns a response with the
    specified object.  Otherwise, it redirects to the specified game
    name.  If the wrapped function set a non-200 status, that will be
    returned as-is.
    """
    def wrapped(self, game_name, *args, **kwargs):
        func(self, game_name, *args, **kwargs)

        if self.status_code == 200:
            if self.message.content_type == 'application/json':
                self.headers['Content-Type'] = 'application/json'
                self.set_body(json.dumps(self.body))
                return self.render()
            else:
                # Brubeck's self.redirect() clears cookies, so we can't use it.
                url = '/%s/' % game_name
                self._finished = True
                msg = 'Page has moved to %s' % url
                self.set_status(302, status_msg=msg)
                self.headers['Location'] = '%s' % url
                return self.render()
        else:
            return self.render()

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


class CreateGameHandler(WebMessageHandler):

    def get(self):
        """
        'Create' a game -- really just forward directly to a game page.
        """
        if self.get_argument('name'):
            return self.redirect('/' + self.get_argument('name') + '/')
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
        block until something happens after id.
        """
        try:
            start_id = int(self.get_argument('id') or -1)
        except ValueError:
            start_id = -1

        info = game.info(self.db_conn, game_name, self.get_player(game_name), start_id)
        context = info.next()

        if self.message.content_type == 'application/json':
            self.headers['Content-Type'] = 'application/json'
            self.set_body(json.dumps(context))
            return self.render()
        else:
            return self.render_template('app', **context)


class ChatHandler(MustacheRendering, PlayerMixin):

    @unquote_game_name
    @redirect_unless_json
    def post(self, game_name):
        """
        Message other players in the game.
        """
        message = self.get_argument('message')
        player = self.get_player(game_name)

        if message and player:
            if game.chat(self.db_conn, game_name, player, message):
                self.set_status(200)
            else:
                self.set_status(400, "Could not send chat")
        elif player is None:
            self.set_status(400, "You are not in this game.")
        else:
            self.set_status(400, "You didn't write a message.")


class JoinHandler(WebMessageHandler, PlayerMixin):

    @unquote_game_name
    @redirect_unless_json
    def post(self, game_name):
        """
        Try to join the game with the post-specified player name `player`.
        If it succeeds, feed the user a cookie!
        """
        if self.get_player(game_name):  # player already in this game
            self.set_status(400, "You are already in this game")
        elif self.get_argument('player'):
            player_name = self.get_argument('player')
            if game.join(self.db_conn, game_name, player_name):
                self.set_cookie(urllib2.quote(game_name, ''), player_name, self.application.cookie_secret)
                self.set_status(200)
            else:
                self.set_status(400, "Could not add %s to game" % player_name)
        else:
            self.set_status(400, "You must specify a name to join a game.")


class StartHandler(WebMessageHandler, PlayerMixin):

    @unquote_game_name
    @redirect_unless_json
    def post(self, game_name):
        """
        Vote to enter temple/advance to next round.
        """
        player = self.get_player(game_name)
        if player:
            game.start(self.db_conn, game_name, player)
            self.set_status(200)
        else:
            self.set_status(400, 'You are not in this game')


class MoveHandler(WebMessageHandler, PlayerMixin):

    @unquote_game_name
    @redirect_unless_json
    def post(self, game_name):
        """
        Looks like we got a Lando!!
        """
        player = self.get_player(game_name)
        if player:
            if game.move(self.db_conn, game_name, player, self.get_argument('move')):
                self.set_status(200)
            else:
                self.set_status(400, 'Could not submit move')
        else:
            self.set_status(400, 'You are not in this game')


config = {
    'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
    'handler_tuples': [(r'^/$', IndexHandler),
                       (r'^/create$', CreateGameHandler),
                       (r'^/(?P<game_name>[^/]+)$', ForwardToGameHandler),
                       (r'^/(?P<game_name>[^/]+)/$', GameHandler),
                       (r'^/(?P<game_name>[^/]+)/join$', JoinHandler),
                       (r'^/(?P<game_name>[^/]+)/start$', StartHandler),
                       (r'^/(?P<game_name>[^/]+)/move$', MoveHandler),
                       (r'^/(?P<game_name>[^/]+)/chat$', ChatHandler)],
    #'cookie_secret': str(uuid.uuid4()),  # this will kill all sessions/games if the server crashes!
    'cookie_secret': 'insecure', # TODO, obvs
    'db_conn': redis.StrictRedis(db=sys.argv[1] if len(sys.argv) > 1 else 'opengold'),
    'template_loader': load_mustache_env('templates')
}


opengold = Brubeck(**config)
opengold.run()
