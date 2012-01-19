class Player(object):
    """
    A player in a game.
    """

    def __init__(self, name):
        self._name = name
        self._artifacts = []
        self._loot = 0

    def take_artifact(self, artifact):
        self._artifacts.append(artifact)

    def take_gold(self, loot):
        self._loot += loot

    # def send(self, message):
    #     print "'%s': %s" % (self.name, message)

    @property
    def name(self):
        return self._name

    @property
    def artifacts(self):
        return self._artifacts

    @property
    def loot(self):
        return self._loot
