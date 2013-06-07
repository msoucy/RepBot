#!/usr/bin/python

import json
import time
import re

from twisted.words.protocols import irc
from twisted.internet import protocol, reactor, ssl

from repsys import ReputationSystem
import admin


def is_rep_change(cmd):
    return cmd.startswith(('++', '--')) or cmd.endswith(('++', '--'))


def parse_rep_change(cng):
    name, op = "", ""
    if cng.startswith(("++", "--")) and cng.endswith(("++", "--")):
        # Should be an error
        pass
    elif cng.startswith(("++", "--")):
        op = cng[:2]
        name = cng[2:]
    elif cng.endswith(("++", "--")):
        op = cng[-2:]
        name = cng[:-2]
    return name, op


def getNameFromIdent(name):
    return name.partition("!")[0]


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
        "ssl": False
    }
    # Add the new stuff
    ret.update(cfg)
    # Fix set information
    ret["ignore"] = sorted(set(ret["ignore"]))
    ret["admins"] = sorted(set(ret["admins"]))
    return ret


class RepBot(irc.IRCClient):

    def __init__(self, cfg):
        self.version = "0.9.0-alpha"
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

    def handleChange(self, user, cmd):
        name, op = parse_rep_change(cmd)
        if name == user:
            self.msg(user, "Cannot change own rep")
            return
        currtime = time.time()
        self.users[user] = [val
                            for val in self.users.get(user, [])
                            if (currtime - val) < self.cfg["timelimit"]]
        if len(self.users[user]) < self.cfg["replimit"]:
            if op == "++":
                self.reps.incr(name)
                self.users[user].append(time.time())
            elif op == "--":
                self.reps.decr(name)
                self.users[user].append(time.time())
        else:
            self.msg(user, "You have reached your rep limit. You can give more rep in {0} seconds"
                     .format(int(self.cfg["timelimit"] - (currtime - self.users[-1]))))

    def ignores(self, user):
        # return user in self.cfg["ignore"]
        for ig in self.cfg["ignore"]:
            if re.search(ig, user) is not None:
                return True
        return False

    def repcmd(self, user, channel, msg):
        # Respond to private messages privately
        if channel == self.cfg["nick"]:
            channel = user

        args = msg.split()
        cmd = args[0] if args else ""
        args = args[1:] if args else []

        if len(args) == 0 and is_rep_change(cmd):
            self.handleChange(user, cmd)
        elif cmd in ("rep",):
            self.msg(channel, self.reps.tell(args[0] if args else user))
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

    def privmsg(self, user, channel, msg):
        if not user:
            return
        user = getNameFromIdent(user)

        if channel != self.cfg["nick"]:
            if msg.startswith(self.cfg["nick"] + ":"):
                msg = msg[len(self.cfg["nick"]) + 1:].strip()
            elif msg.startswith('!'):
                msg = msg[1:]
            elif not is_rep_change(msg):
                return
        elif msg.startswith('!'):
            msg = msg[1:]

        if self.ignores(user):
            self.msg(
                user,
                "You have been blocked from utilizing my functionality.")
        elif channel == self.cfg["nick"]:
            # It's a private message
            isAdmin = False
            if msg.startswith("admin"):
                msg = msg.replace("admin", "", 1)
                isAdmin = True
            elif msg.startswith("@"):
                msg = msg[1:]
                isAdmin = True

            if isAdmin:
                if user in self.cfg["admins"]:
                    self.admin(user, msg)
                else:
                    self.log("Admin attempt from " + user)
                    self.msg(user, "You are not an admin.")
            else:
                self.repcmd(user, channel, msg)

        elif not self.cfg["privonly"]:
            # I'm just picking up a regular chat
            # And we aren't limited to private messages only
            self.repcmd(user, channel, msg)

    def log(self, msg):
        print time.asctime(), msg

    def save(self):
        self.reps.dump()
        fi = open("data/settings.txt", "w")
        json.dump(cfg, fi)
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
