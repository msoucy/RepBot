#!/usr/bin/python

import time
import re

from twisted.words.protocols import irc
from twisted.internet import protocol, reactor, ssl
from twisted.internet.task import LoopingCall

from backend_yaml import ReputationSystemYAML
from .ReputationBot import ReputationBot
from repcmds import get_rep_change
import admin
from config import Config

def ident_to_name(name):
    return name.split("!", 1)[0]

class RepBot(irc.IRCClient):

    def __init__(self, cfg, bot):
        self.version = "0.13.0"
        self.cfg = cfg

        self.users = {}

        # Instance variables for irc.IRCClient
        self.nickname = cfg.nick
        self.realname = cfg.realname
        self.sourceURL = "http://github.com/msoucy/RepBot"
        self.versionName = "RepBot"
        self.versionNum = self.version

        self.rebuild_wildcards()
        self.changed = False
        self.saver = LoopingCall(self.save)
        self.saver.start(self.cfg.savespeed)

        self.bot = bot

    def signedOn(self):
        print "Signed on as {0}.".format(self.nickname)
        for chan in self.cfg["channels"]:
            self.join(chan)

    def irc_unknown(self, prefix, command, params):
        if command == "INVITE":
            self.log("Invite to {1} from {0}".format(prefix, params[1]))
            self.join(params[1])

    def joined(self, channel):
        print "Joined {0}.".format(channel)

    def log(self, msg):
        print time.asctime(), msg

    def save(self):
        if not self.changed: return
        self.changed = False
        self.cfg.save()
        self.log("Saved data")

    def rebuild_wildcards(self):
        def wildcard_regex(w):
            return w.replace('.','\\.').replace('?','.').replace('*','.*?')
        def regex_list(l):
            return [re.compile(wildcard_regex(x)) for x in l]
        self.adminList = regex_list(self.cfg.admins)
        self.ignoreList = regex_list(self.cfg.ignore)

    def hasadmin(self, user):
        return any(u.match(user) for u in self.adminList)

    def ignores(self, user):
        return any(u.match(user) for u in self.ignoreList)

    def handle(self, user, changer):
        currtime = time.time()
        # Filter old uses
        self.users[user] = [val
                            for val in self.users.get(user, [])
                            if (currtime - val) < self.cfg.timelimit]
        if len(self.users[user]) < self.cfg.replimit:
            self.bot.handle(self, user, changer)
            self.users[user].append(currtime)
            self.changed = True
        else:
            self.send_to(user, "You have reached your rep limit. You can give more rep in {0} seconds"
                     .format(int(self.cfg.timelimit - (currtime - self.users[user][-1]))))

    def report(self, chan):
        admin.admin(self, chan, "report")

    def send_to(self, dest, *args, **kwargs):
        return self.msg(dest, *[a.encode("utf-8") for a in args], **kwargs)

    def send_help(self, user):
        send = lambda msg: self.send_to(user, msg)
        send('Message me with "!rep <name>" to get the reputation of <name>')
        send('Use prefix or postfix ++/-- to change someone\'s rep.')
        send('You are not able to change your own rep.')
        send('Message me with "!version" to see my version number')

    def canonical_name(self, user):
        return re.split(r"[\|`:]", user)[0].lower()

    def privmsg(self, ident, channel, msg):
        if not ident:
            return

        try:
            msg = msg.decode("utf-8")
        except UnicodeDecodeError as ue:
            self.log("Received non-unicode message")
            return
        isAdmin = False
        if msg.startswith('!'):
            # It's a command to RepBot itself
            msg = msg[1:]
        elif channel != self.nickname and msg.startswith(self.nickname + ":"):
            # It's a command to RepBot itself
            msg = msg[len(self.nickname) + 1:].strip()
        elif self.hasadmin(ident) and channel == self.nickname:
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

        if self.cfg.spy:
            self.log("[{0}]\t{1}:\t{2}".format(channel, ident, msg))

        if isAdmin:
            admin.admin(self, user, msg)
        elif channel == self.nickname or not self.cfg.privonly:
            # I'm just picking up a regular chat
            # And we aren't limited to private messages only
            self.bot.repcmd(self, user, msg, channel if channel != self.nickname else None)


class RepBotFactory(protocol.ClientFactory):

    def __init__(self, cfg, bot):
        self.cfg = cfg
        self.bot = bot

    def buildProtocol(self, addr):
        return RepBot(self.cfg, self.bot)

    def clientConnectionLost(self, connector, reason):
        print "Lost connection (%s), reconnecting." % (reason,)
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "Could not connect: %s" % (reason,)

if __name__ == "__main__":
    cfg = Config("data/settings.txt")
    bot = ReputationBot(ReputationSystemYAML(cfg.reps))
    server = cfg.server
    port = cfg.port
    factory = RepBotFactory(cfg, bot)
    print "Connecting to {0}:{1}".format(server, port)
    if cfg.ssl:
        print "Using SSL"
        reactor.connectSSL(server, port, factory, ssl.ClientContextFactory())
    else:
        print "Not using SSL"
        reactor.connectTCP(server, port, factory)
    reactor.run()
