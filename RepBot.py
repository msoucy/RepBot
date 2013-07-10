#!/usr/bin/python

import json
import time
import re

from twisted.words.protocols import irc
from twisted.internet import protocol, reactor, ssl

from repsys import ReputationSystem
import admin
import random

class RepChangeCommand(object):
    def __init__(self):
        self.valid = False
        self.user = None

    def isValid(self):
        return self.valid

    def getUser(self):
        return self.user

    def setValid(self, valid):
        self.valid = valid

    def setUser(self, user):
        self.user = canonical_name(user)
        if not self.user:
            self.setValid(False)

    def perform(self, val):
        return NotImplemented

class X86RepChange(RepChangeCommand):
    def __init__(self, msg):
        super(X86RepChange, self).__init__()

        m = msg.lower().split()
        self.atomic = False

        if len(m) < 2:
            return
        if m[0] == "lock":
            self.atomic = True
            m = m[1:]
            if len(m) < 2:
                return
        suffix = self.getSuffix().lower()
        if m[0] == "inc" + suffix:
            self.op = "inc"
        elif m[0] == "dec" + suffix:
            self.op = "dec"
        else:
            return

        self.setUser(m[1])
        self.setValid(True)

    def getBits(self):
        return NotImplemented

    def getSuffix(self):
        return NotImplemented

    def perform(self, val):
        if not self.atomic and random.randint(1, 100) <= 10:
            return val
        bits = self.getBits() - 1
        maxval = (2**bits)-1
        minval = -1 * (2**bits)
        if self.op == "inc":
            if val >= maxval:
                return minval
            else:
                return val + 1
        elif self.op == "dec":
            if val <= minval:
                return maxval
            else:
                return val - 1

class X86_64RepChange(X86RepChange):
    def getSuffix(self):
        return "q"

    def getBits(self):
        return 64

class X86_32RepChange(X86RepChange):
    def getSuffix(self):
        return "l"

    def getBits(self):
        return 32

class X86_16RepChange(X86RepChange):
    def getSuffix(self):
        return "w"

    def getBits(self):
        return 16

class X86_8RepChange(X86RepChange):
    def getSuffix(self):
        return "b"

    def getBits(self):
        return 8

class GPlusRepChange(RepChangeCommand):
    def __init__(self, msg):
        super(GPlusRepChange, self).__init__()

        m = msg.lower().split()
        if len(m) != 2:
            return

        if m[1] not in ["+1","-1"]:
            return

        self.setUser(m[0])
        self.op = m[1]

        self.setValid(True)

    def perform(self, val):
        if self.op == "+1":
            return val + 1
        elif self.op == "-1":
            return val - 1

class PrePostfixRepChange(RepChangeCommand):
    def __init__(self, msg):
        super(PrePostfixRepChange, self).__init__()

        starts = msg.startswith(('++', '--'))
        ends = msg.endswith(('++', '--'))

        if (starts and ends) or (not starts and not ends):
            return

        if starts:
            self.setUser(msg[2:])
            self.op = msg[:2]

        if ends:
            self.setUser(msg[:-2])
            self.op = msg[-2:]

        if len(self.getUser().split()) == 1:
            self.setValid(True)

    def perform(self, val):
        if self.op == "++":
            return val + 1
        elif self.op == "--":
            return val - 1

class PDP8RepChange(RepChangeCommand):
    def __init__(self, msg):
        super(PDP8RepChange, self).__init__()

        m = msg.lower().split()

        if len(m) != 2 or m[1] != "iac" or m[0][-1] != ":":
            return

        self.setUser(m[0][:-1])
        self.setValid(True)

    def perform(self, val):
        return val + 1

class RepChangeCommandFactory(object):
    REP_CHANGERS = [
        PrePostfixRepChange,
        GPlusRepChange,
        X86_64RepChange,
        X86_32RepChange,
        X86_16RepChange,
        X86_8RepChange,
        PDP8RepChange
    ]

    def parse(self, msg):
        for changer in self.REP_CHANGERS:
            c = changer(msg)
            if c.isValid():
                return c
        return None


def canonical_name(user):
    return re.split(r"[\|`:]", user)[0].lower()

def ident_to_name(name):
    return name.split("!", 1)[0]

def wildcard_mask(wilds):
    return wilds.replace('?','.').replace('*','.*?')

def wildcard_matches(wild, s):
    return re.match(wildcard_mask(wild), s) is not None

def normalize_config(cfg):
    # Default settings
    ret = {
        "reps": "data/reps.txt",
        "ignore": [],
        "admins": [],
        "replimit": 5,
        "timelimit": 60.0 * 60.0,
        "privonly": False,
        "autorespond": False,
        "nick": "RepBot",
        "realname": "Reputation Bot",
        "servname": "Reputation Bot",
        "channels": [],
        "server": "",
        "port": 6667,
        "ssl": False,
        "spy": False
    }
    # Add the new stuff
    ret.update(cfg)
    # Fix set information
    ret["ignore"] = sorted(set(ret["ignore"]))
    ret["admins"] = sorted(set(ret["admins"]))
    ret["nick"] = ret["nick"].decode('ascii')
    return ret


class RepBot(irc.IRCClient):

    def __init__(self, cfg):
        self.version = "0.10.0"
        self.cfg = cfg

        self.users = {}
        self.reps = ReputationSystem(cfg["reps"])

        # Instance variables for irc.IRCClient
        self.nickname = cfg["nick"]
        self.realname = cfg["realname"]
        self.sourceURL = "http://github.com/msoucy/RepBot"
        self.versionName = "RepBot"
        self.versionNum = self.version

    def signedOn(self):
        print "Signed on as {0}.".format(self.cfg["nick"])
        for chan in self.cfg["channels"]:
            self.join(chan)

    def joined(self, channel):
        print "Joined {0}.".format(channel)

    def admin(self, user, msg):
        admin.admin(self, user, msg)

    def handleChange(self, user, changer):
        name = changer.getUser()
        if name == canonical_name(user):
            self.msg(user, "Cannot change own rep")
            return
        currtime = time.time()
        self.users[user] = [val
                            for val in self.users.get(user, [])
                            if (currtime - val) < self.cfg["timelimit"]]
        if len(self.users[user]) < self.cfg["replimit"]:
            rep = self.reps.get(name)
            self.reps.set(name, changer.perform(rep))
            self.users[user].append(time.time())
        else:
            self.msg(user, "You have reached your rep limit. You can give more rep in {0} seconds"
                     .format(int(self.cfg["timelimit"] - (currtime - self.users[user][-1]))))

    def ignores(self, user):
        for ig in self.cfg["ignore"]:
            if wildcard_matches(ig, user):
                return True
        return False
    
    def hasadmin(self, user):
        for adm in self.cfg["admins"]:
            if wildcard_matches(adm, user):
                return True
        return False

    def repcmd(self, user, channel, msg):
        # Respond to private messages privately
        if channel == self.cfg["nick"]:
            channel = user

        args = msg.split()
        cmd = args[0] if args else ""
        args = args[1:] if args else []
        changer = RepChangeCommandFactory().parse(msg)

        if changer != None:
            self.handleChange(user, changer)
        elif cmd in ("rep",):
            self.msg(channel, self.reps.tell(canonical_name(args[0] if args else user)))
        elif cmd in ("top", "report"):
            self.msg(user, self.reps.report(True))
        elif cmd in ("ver", "version", "about"):
            self.msg(channel, 'I am RepBot version {0}'.format(self.version))
        elif cmd in ("help",):
            self.msg(
                channel,
                'Message me with "!rep <name>" to get the reputation of <name>')
            self.msg(
                channel,
                'Use prefix or postfix ++/-- to change someone\'s rep. You are not able to change your own rep.')
            self.msg(
                channel,
                'Message me with "!version" to see my version number')
        elif self.cfg["autorespond"] and channel == user:
            # It's not a valid command, so let them know
            # Only respond privately
            self.msg(
                user,
                'Invalid command. MSG me with !help for information')

    def privmsg(self, ident, channel, msg):
        if not ident:
            return

        msg = msg.decode("utf-8")
        isAdmin = False
        if msg.startswith('!'):
            # It's a command to RepBot itself
            msg = msg[1:]
        elif channel != self.cfg["nick"] and msg.startswith(self.cfg["nick"] + ":"):
            # It's a command to RepBot itself
            msg = msg[len(self.cfg["nick"]) + 1:].strip()
        elif self.hasadmin(ident) and channel == self.cfg["nick"]:
            # They have admin access, check for commands
            if msg.startswith("admin"):
                msg = msg.replace("admin", "", 1)
            elif msg.startswith("@"):
                msg = msg[1:]
            else:
                return
            isAdmin = True
        elif RepChangeCommandFactory().parse(msg) == None:
            # It doesn't match a rep change
            return

        user = ident_to_name(ident)
        if self.ignores(ident) and not self.hasadmin(ident):
            self.msg(
                user,
                "You have been blocked from utilizing my functionality.")

        if self.cfg["spy"]:
            self.log("[{1}]\t{0}:\t{2}".format(ident, channel, msg))

        if isAdmin:
            self.admin(user, msg)
        elif channel == self.cfg["nick"] or not self.cfg["privonly"]:
            # I'm just picking up a regular chat
            # And we aren't limited to private messages only
            self.repcmd(user, channel, msg)

    def log(self, msg):
        print time.asctime(), msg

    def save(self):
        self.reps.dump()
        fi = open("data/settings.txt", "w")
        json.dump(cfg, fi, sort_keys=True, indent=4, separators=(',', ': '))
        fi.close()


class RepBotFactory(protocol.ClientFactory):

    def __init__(self, cfg):
        self.cfg = cfg

    def buildProtocol(self, addr):
        return RepBot(self.cfg)

    def clientConnectionLost(self, connector, reason):
        print "Lost connection (%s), reconnecting." % (reason,)
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "Could not connect: %s" % (reason,)

if __name__ == "__main__":
    cfg = normalize_config(json.load(open("data/settings.txt")))
    server = cfg["server"]
    port = cfg["port"]
    factory = RepBotFactory(cfg)
    print "Connecting to {0}:{1}".format(server, port)
    if cfg["ssl"]:
        print "Using SSL"
        reactor.connectSSL(server, port, factory, ssl.ClientContextFactory())
    else:
        print "Not using SSL"
        reactor.connectTCP(server, port, factory)
    reactor.run()
