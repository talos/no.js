class Player(object):
    """
    A player in a game.
    """

    def __init__(self, name):
        self.name = name
        self.artifacts = []
        self.loot = 0

    def take_artifact(self, artifact):
        self.artifacts.append(artifact)

    def take_gold(self, loot):
        self.loot += loot

    def send(self, message):
        print "'%s': %s" % (self.name, message)
