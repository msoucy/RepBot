import json
import operator
import os.path

from .interfaces import ReputationInterface

REPFILE = "data/reps.txt"

class ReputationSystemYAML(ReputationInterface):
    __slots__ = ('reps', 'ignorelist', 'cached', 'repfile')

    def __init__(self, repfile=REPFILE):
        self.reps = {}
        self.ignorelist = set()
        self.repfile = os.path.normpath(repfile)
        self.load(self.repfile)
        self.filter()

    #######################################################################################
    # ReputationInterface

    def save(self):
        self.filter()
        with open(self.repfile, "w") as fi:
            json.dump(self.reps, fi, sort_keys=True, indent=4, separators=(',', ': '))

    def load(self):
        if not os.path.exists(self.repfile):
            self.reps = {}
        else:
            with open(self.repfile) as fi:
                self.reps = json.load(fi)

    def get(self, name):
        return self.reps.get(name, 0)

    def apply(self, changer):
        self.reps[changer.getUser()] = changer.perform(self.get(changer.getUser()))

    def set(self, name, val):
        self.reps[name] = int(val)

    def top(self,  N=5):
        sorted_reps = sorted(self.reps.iteritems(),
                             key=operator.itemgetter(1),
                             reverse=True)
        highest = sorted_reps[:N]
        lowest = sorted_reps[-N:]
        return (highest, lowest)

    #######################################################################################
    # Extra systems

    def filter(self):
        self.reps = {key: val for key, val in self.reps.items() if val != 0}

    def report(self):
        self.filter()
        highest, lowest = self.top()
        val = lambda name, score: "{0}: {1}".format(name.encode('unicode-escape'), score)
        return "Top reps: {0}\nBottom reps: {1}".format(
            ", ".join(val(name, score) for name, score in highest),
            ", ".join(val(name, score) for name, score in lowest))

    def tell(self, name):
        self.filter()
        return "Rep for {0}: {1}".format(name.encode('unicode-escape'), self.get(name))

