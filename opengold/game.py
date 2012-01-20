from deck import Deck
from round import Round
from player import Player
import message

MAX_ROUNDS = 5

class Game(object):

    def __init__(self, name):
        """
        Generate a new game with the specified name.
        """
        self._players = {}
        self._victors = []
        self._deck = Deck()
        self._name = name
        self._round_num = 0

    def _next_round(self):
        """
        Advance to the next round.  We have to add an artifact into the deck.
        """
        self._round_num += 1
        self._deck.add_artifact()
        self._round = Round(self._players.values(), self._deck)

    # def _determine_victors(self):
    #     """
    #     Return the players with the most points, breaking tie with
    #     artifacts.  Ties only happen if there are identical points and
    #     artifacts.
    #     """
    #     by_loot = {}
    #     for player in self._players:
    #         loot = player.loot
    #         by_loot[loot] = by_loot.get(loot, []) + [player]

    #     most_loot = sorted(by_loot.keys(), reverse=True)[0]
    #     candidates = by_loot[most_loot]

    #     by_artifacts = {}
    #     for candidate in candidates:
    #         artifacts = len(candidate.artifacts)
    #         by_artifacts[artifacts] = by_artifacts.get(artifacts, []) + [candidate]
    #     most_artifacts = sorted(by_artifacts.keys(), reverse=True)[0]

    #     return by_artifacts[most_artifacts]

    def _broadcast_status(self):
        """
        Broadcast game status to all players.
        """
        for player in self._players.values():
            player.send(self.get_status(player.name))

    def add_player(self, player_name):
        """
        Add a player to the game.  Returns True if they have been
        added, or False otherwise
        """
        if (self._round_num is 0) and (not player_name in self._players.keys()):
            self._players[player_name] = Player(player_name)
            return True
        else:
            return False

    def chat(self, speaker, content):
        """
        Broadcast chat message to all players.
        """
        for player in self._players.values():
            player.send(message.chat(speaker, content))

    def start(self, player_name):
        """
        Player_name wants to start.  If all players have done this,
        then the game starts.  This stops new players from joining.
        Returns True if the game has been started, False otherwise.

        A single player cannot start a game.
        """
        player = self._players.get(player_name)

        if player:
            player.start()
            if self._round_num is 0 and len(self._players) > 1:
                if len(filter(lambda p: p.started is False, self._players.values())) is 0:
                    self._next_round()
                    return True
                self._broadcast_status()

        return False

    def poll(self, player_name):
        """
        Poll messages for a player by name.  Returns none if there is no player
        by that name, or no messages for that player.
        """
        player = self._players.get(player_name)

        if player:
            return player.poll()
        else:
            return None

    def get_status(self, player_name=None):
        """
        The game's current status as a python object.  If None is
        passed for player_name, then no player-specific data will be
        returned.
        """
        if self._round_num is 0:
            return message.not_yet_started(self._players.values())
        elif self._round_num > 0 and self._round_num < MAX_ROUNDS:
            return message.in_progress(
                self._players.values(),
                self._round.players_in_play,
                self._round.deal,
                self._deck.artifacts,
                self._round.table,
                self._round.taken,
                self._round.pot,
                self._round_num,
                self._players.get(player_name, None))
        else:
            return message.finished(self._players.values(), self._round_num)

    def submit(self, player_name, move):
        """
        Submit a move for the specified player in the current round.
        Returns True if the move was submitted, False otherwise.
        """
        player = self._players.get(player_name)

        if player:
            if(self._round_num > 0 and
               self._round_num < MAX_ROUNDS and
               self._round.submit(player, move)):

                self._broadcast_status()

                if self._round.is_over():
                    if(self._round_num < MAX_ROUNDS):
                        self._next_round()
                    else:
                        #self._victors = self._determine_victors()
                        self._broadcast_status()

                return True

        return False
