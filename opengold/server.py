#!/usr/bin/env python

import uuid
import redis
import json
import sys

import game
from templating import load_mustache_env, MustacheRendering

from brubeck.request_handling import Brubeck, WebMessageHandler

class PlayerMixin():
    """
    This mixin provides a get_player() method.
    """

    def get_player(self, game_name):
        """
        Get the player for the specified game_name, or None if the
        user is not taking part.
        """
        return self.get_cookie(game_name, None, self.application.cookie_secret)


# class IndexHandler(Jinja2Rendering):

#     def get(self):
#         """
#         List all games currently available.
#         """
#         names = game.list_names(self.db_conn)
#         self.set_body(json.dumps(names))


        # if self.get_argument('game'):
        #     return self.redirect(self.get_argument('game'))
        # else:
        #     context = {
        #         'games': [{ 'name': name,
        #                     # todo this will lock all games!
        #                     'status': game.get_status(self.db_conn, name) }
        #                   for name in game.list_names(self.db_conn)]
        #         }
        #     return self.render_template('index.html', **context)

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
            return self.render_template('index.html', **context)

class GameHandler(MustacheRendering, PlayerMixin):

    def get(self, game_name):
        """
        Get information about happenings in game since id.  Will
        block until something happens after id.  ID defaults to 0.
        """
        start_id = self.get_argument('id') or 0
        context = game.get_info(self.db_conn, game_name, self.get_player(game_name), start_id)
        if self.message.content_type == 'application/json':
            self.headers['Content-Type'] = 'application/json'
            self.set_body(json.dumps(context))
            return self.render()
        else:
            return self.render_template('app.html', **context)

class ChatHandler(WebMessageHandler, PlayerMixin):

    def post(self, game_name):
        """
        Message other players in the game.
        """
        message = self.get_argument('message')
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


class JoinHandler(WebMessageHandler, PlayerMixin):

    def post(self, game_name):
        """
        Try to join the game with the post-specified player name `player`.
        If it succeeds, feed the user a cookie!
        """
        if self.get_player(game_name):  # player already in this game
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


class EnterTempleHandler(WebMessageHandler, PlayerMixin):

    def post(self, game_name):
        """
        Vote to enter temple/advance to next round.
        """
        player = self.get_player(game_name)
        if player:
            game.enter_temple(self.db_conn, game_name, player)
            self.set_status(200)
            #self.redirect('/%s' % kwargs['game_name'])
        else:
            self.set_status(400, status_msg="You are not in this game")

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
                       (r'^/(?P<game_name>[^/]+)/join$', JoinHandler),
                       (r'^/(?P<game_name>[^/]+)/enter$', EnterTempleHandler),
                       (r'^/(?P<game_name>[^/]+)/move$', MoveHandler)],
                       #(r'^/(?P<game_name>[^/]+)/poll$', PollHandler)],
    'cookie_secret': str(uuid.uuid4()),  # this will kill all sessions/games if the server crashes!
    'db_conn': redis.StrictRedis(db=sys.argv[1] or 'opengold'),
    'template_loader': load_mustache_env('templates')
}


app = Brubeck(**config)
app.run()
