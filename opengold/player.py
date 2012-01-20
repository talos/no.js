class Player(object):
    """
    A player in a game.
    """

    def __init__(self, name):
        self._name = name
        self._started = False
        self._artifacts = []
        self._loot = 0
        self._message_queue = []

    def take_artifact(self, artifact):
        self._artifacts.append(artifact)

    def take_gold(self, loot):
        self._loot += loot

    def start(self):
        """
        Vote to start.
        """
        self._started = True

    def send(self, message):
        """
        Add a message to the queue.
        """
        self._message_queue.append(message)

    def poll(self):
        """
        Receive a message from the queue.  Returns None if the queue is empty.
        """
        if len(self._message_queue):
            return self._message_queue.pop(0)
        else:
            return None

    @property
    def name(self):
        return self._name

    @property
    def artifacts(self):
        return self._artifacts

    @property
    def loot(self):
        return self._loot

    @property
    def started(self):
        """
        Returns True if the player voted to start, False otherwise.
        """
        return self._started
