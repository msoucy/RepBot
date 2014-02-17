import abc

class SendingFrontend(object):
    'Abstract Frontend implementation'
    def send_to(self, , msg):
        raise NotImplementedError
    def send_help(self):
        raise NotImplementedError

class ReputationInterface(object):

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def save(self):
        'Force a save to the backend'

    @abc.abstractmethod
    def load(self):
        'Force a reload from the backend'

    @abc.abstractmethod
    def get(self, name):
        "Get the reputation for a name"

    @abc.abstractmethod
    def apply(self, changer):
        "Applies the given changer to the given name"

    @abc.abstractmethod
    def set(self, name, value):
        "Force sets a name's reputation"

    @abc.abstractmethod
    def top(self, N=5):
        'Get the top (and bottom) N reputations'

