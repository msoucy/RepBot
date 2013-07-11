import json
import operator
import os.path


class ReputationSystem(object):
    __slots__ = ('reps', 'ignorelist', 'cached', 'repfile')

    def __init__(self, repfile="data/reps.txt"):
        self.reps = {}
        self.ignorelist = set()
        self.repfile = os.path.normpath(repfile)
        self.load(repfile)
        self.filter()

    def dump(self):
        self.filter()
        fi = open(self.repfile, "w")
        json.dump(self.reps, fi, sort_keys=True, indent=4, separators=(',', ': '))
        fi.close()

    def load(self, repfile="data/reps.txt"):
        if not os.path.exists(repfile):
            self.reps = {}
            self.dump()
            return
        fi = open(self.repfile)
        self.reps = json.load(fi)
        fi.close()

    def get(self, name):
        return self.reps.get(name, 0)

    def set(self, name, val):
        self.reps[name] = int(val)

    def apply(self, changer):
        self.reps[changer.getUser()] = changer.perform(self.reps[changer.getUser()])

    def clear(self, name):
        self.reps.pop(name.strip(), None)

    def filter(self):
        self.reps = {key: val for key, val in self.reps.items() if val != 0}

    def report(self, force=False):
        self.filter()
        sorted_reps = sorted(self.reps.iteritems(),
                             key=operator.itemgetter(1),
                             reverse=True)
        highest = sorted_reps[:5]
        lowest = sorted_reps[-5:]
        return "Top reps: {0}\nBottom reps: {1}".format(
            ", ".join("{0}: {1}".format(name, score) for name, score in sorted_reps[:5]),
            ", ".join("{0}: {1}".format(name, score) for name, score in sorted_reps[-5:]))

    def tell(self, name):
        self.filter()
        return "Rep for {0}: {1}".format(name, self.get(name))

    def all(self):
        self.filter()
        return "All reps: {0}".format(self.reps)

