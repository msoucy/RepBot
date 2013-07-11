#!/usr/bin/python

import json
import time
import re

from twisted.words.protocols import irc
from twisted.internet import protocol, reactor, ssl

from repsys import ReputationSystem
from repcmds import get_rep_change
import admin

def canonical_name(user):
    return re.split(r"[\|`:]", user)[0].lower()

def ident_to_name(name):
    return name.split("!", 1)[0]

def normalize_config(cfgFilename):
    # Default settings
    ret = {
        "reps": "data/reps.txt",
        "ignore": [],
        "admins": [],
        "replimit": 5,
        "timelimit": 5.0 * 60.0,
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
    ret.update(json.load(open(cfgFilename)))
    # Write the full config file, so they have a full listing
    with open(cfgFilename,'w') as of:
        json.dump(ret, of, sort_keys=True, indent=4, separators=(',', ': '))
    # Fix set information
    ret["ignore"] = sorted(set(ret["ignore"]))
    ret["admins"] = sorted(set(ret["admins"]))
    ret["nick"] = ret["nick"].decode('ascii')
    
    def cleanup(item):
        if isinstance(item, dict):
            return {name:cleanup(val) for name, val in item.items()}
        elif isinstance(item, list):
            return [cleanup(x) for x in item]
        elif isinstance(item, basestring):
            return str(item)
        else:
            return item
    return cleanup(ret)


class RepBot(irc.IRCClient):

    def __init__(self, cfg):
        self.version = "0.11.0"
        self.cfg = cfg

        self.users = {}
        self.reps = ReputationSystem(cfg["reps"])

        # Instance variables for irc.IRCClient
        self.nickname = cfg["nick"]
        self.realname = cfg["realname"]
        self.sourceURL = "http://github.com/msoucy/RepBot"
        self.versionName = "RepBot"
        self.versionNum = self.version

        self.rebuild_wildcards()

    def signedOn(self):
        print "Signed on as {0}.".format(self.cfg["nick"])
        for chan in self.cfg["channels"]:
            self.join(chan)

    def joined(self, channel):
        print "Joined {0}.".format(channel)

    def log(self, msg):
        print time.asctime(), msg

    def save(self):
        self.reps.dump()
        fi = open("data/settings.txt", "w")
        json.dump(cfg, fi, sort_keys=True, indent=4, separators=(',', ': '))
        fi.close()

    def rebuild_wildcards(self):
        def wildcard_regex(w):
            return w.replace('.','\\.').replace('?','.').replace('*','.*?')
        def regex_list(l):
            return [re.compile(wildcard_regex(x)) for x in l]
        self.adminList = regex_list(self.cfg["admins"])
        self.ignoreList = regex_list(self.cfg["admins"])

    def hasadmin(self, user):
        for adm in self.adminList:
            if adm.match(user):
                return True
        return False

    def ignores(self, user):
        for ig in self.ignoreList:
            if ig.match(user):
                return True
        return False

    def handleChange(self, user, changer):
        name = changer.getUser()
        if name == canonical_name(user):
            self.msg(user, "Cannot change own rep")
            return
        currtime = time.time()
        # Filter old uses
        self.users[user] = [val
                            for val in self.users.get(user, [])
                            if (currtime - val) < self.cfg["timelimit"]]
        if len(self.users[user]) < self.cfg["replimit"]:
            self.reps.apply(changer.perform(rep))
            self.users[user].append(currtime)
        else:
            self.msg(user, "You have reached your rep limit. You can give more rep in {0} seconds"
                     .format(int(self.cfg["timelimit"] - (currtime - self.users[user][-1]))))

    def repcmd(self, user, channel, msg):
        # Respond to private messages privately
        if channel == self.cfg["nick"]:
            channel = user

        args = msg.split()
        cmd = args[0] if args else ""
        args = args[1:] if args else []
        changer = get_rep_change(msg)

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
        elif get_rep_change(msg) == None:
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
            admin.admin(self, user, msg)
        elif channel == self.cfg["nick"] or not self.cfg["privonly"]:
            # I'm just picking up a regular chat
            # And we aren't limited to private messages only
            self.repcmd(user, channel, msg)


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
    cfg = normalize_config("data/settings.txt")
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
