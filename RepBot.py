#!/usr/bin/python

import sys, ConfigParser
from twisted.words.protocols import irc
from twisted.internet import protocol, reactor, ssl
from repsys import ReputationSystem

def getNameFromIdent(name):
	return name.partition("!")[0]

class RepBot(irc.IRCClient):
	nickname = property(lambda self:self.factory.nickname)
	realname = property(lambda self:self.factory.realname)
	cfg = property(lambda self:self.factory.cfg)
	
	def __init__(self):
		self.version = "0.7.1"
		self.reps = ReputationSystem(self.cfg.get("RepBot","reps")
									 if self.cfg.has_option("RepBot","reps")
									 else "data/reps.txt")
		self.ignorelist = set((self.cfg.get("RepBot","ignore")
					if self.cfg.has_option("RepBot","ignore")
					else "").split())
		self.admins = set((self.cfg.get("RepBot","admins")
					if self.cfg.has_option("RepBot","admins")
					else "").split())
		self.privonly = False
		self.autorespond = False

	def signedOn(self):
		self.join(self.factory.channel)
		print "Signed on as {0}.".format(self.nickname)

	def joined(self, channel):
		print "Joined {0}.".format(channel)
	
	def admin(self, user, msg):
		if not msg.strip(): return
		command = msg.split()[0]
		args = msg.split()[1:]
		if command == "verify":
			self.msg(user, "Admin authenticated!")
		elif command == "admin":
			self.admins |= set(args)
		elif command == "unadmin":
			self.admins -= set(args)
		elif command == "ignore":
			self.ignorelist |= set(args)
		elif command == "unignore":
			self.ignorelist -= set(args)
		elif command == "ignorelist":
			print list(self.ignorelist)
		elif command == "dump":
			self.reps.dump()
			print "Rep file dumped"
		elif command == "filter":
			self.reps.filter()
			self.admin(user,"all")
		elif command == "clear":
			for name in args:
				self.reps.clear(name)
		elif command == "tell":
			channel = (args[0]
						if args and args[0].startswith(('#','&','+','!'))
						else user)
			for name in args:
				self.msg(channel, self.reps.tell(name))
		elif command == "all":
			channel = (args[0]
						if args and args[0].startswith(('#','&','+','!'))
						else user)
			for name in args:
				self.msg(channel, self.reps.all())
		elif command in ["auto", "autorespond"]:
			self.autorespond = (args[0]=="on")
		elif command == "private":
			self.privonly = (args[0]=="on")
		elif command == "clearall":
			self.reps.reps = {}
		elif command == "report":
			channel = (args[0]
						if args and args[0].startswith(('#','&','+','!'))
						else user)
			self.msg(channel, self.reps.report())
		elif command == "apply":
			self.reps.update(eval("".join(args)))
		elif command == "term" and len(args) > 1:
			self.part(args[0], " ".join(args[1:]))
			sys.exit(0)
		else:
			print "Invalid command {0}".format(command)
	
	def repcmd(self, user, channel, msg):
		def parseName(name):
			name = name[:-2].strip()
			return name
		# Respond to private messages privately
		if channel == self.nickname:
			channel = user
		if msg.endswith(('++','--')) and parseName(msg) != user:
			if msg.endswith("++"):
				name = parseName(msg)
				if ' ' not in name:
					self.reps.incr(name)
			elif msg.endswith("--"):
				name = parseName(msg)
				if ' ' not in name:
					self.reps.decr(name)
		elif msg.startswith("!rep"):
			msg=msg.replace("!rep","").strip()
			self.msg(channel, self.reps.tell(msg if msg else user))
		elif msg.startswith("!ver"):
			self.msg(channel, 'I am RepBot version {0}'.format(self.version))
		elif msg.startswith("!help"):
			self.msg(channel, 'Message me with "!rep <name>" to get the reputation of <name>')
			self.msg(channel, 'Message me with "<name>++" or "<name>--" to change the reputation of <name>. You are not able to change your own rep.')
			self.msg(channel, 'Message me with "!version" to see my version number')
		elif self.autorespond and channel == user:
			# It's not a valid command, so let them know
			# Only respond privately
			self.msg(channel, 'Invalid command. MSG me with !help for information')

	def privmsg(self, user, channel, msg):
		if not user: return
		user = getNameFromIdent(user)
		if user in self.ignorelist:
			self.msg(user, "You have been blocked from utilizing my functionality.")
			return
		if channel == self.nickname:
			# It's a message just to me
			if msg.startswith("!admin"):
				if user in self.admins:
					self.admin(user, msg.replace("!admin","").strip())
				else:
					print "Admin attempt from",user
					self.msg(user, "You are not an admin.")
			else:
				self.repcmd(user, channel, msg)
		elif not self.privonly:
			# I'm just picking up a regular chat
			# And we aren't limited to private messages only
			self.repcmd(user, channel, msg)


class RepBotFactory(protocol.ClientFactory):
	protocol = RepBot

	def __init__(self, channel, cfg, nickname='RepBot', realname="Reputation Bot"):
		self.channel = channel
		self.nickname = nickname
		self.realname = realname
		self.cfg = cfg

	def clientConnectionLost(self, connector, reason):
		print "Lost connection (%s), reconnecting." % (reason,)
		connector.connect()

	def clientConnectionFailed(self, connector, reason):
		print "Could not connect: %s" % (reason,)

if __name__ == "__main__":
	cfg = ConfigParser.RawConfigParser()
	cfg.read("data/settings.txt")
	server = cfg.get("RepBot","server") if cfg.has_option("RepBot","server") else ""
	port = cfg.getint("RepBot","port") if cfg.has_option("RepBot","port") else 6667
	channel = cfg.get("RepBot","channel") if cfg.has_option("RepBot","channel") else ""
	nickname = cfg.get("RepBot","nick") if cfg.has_option("RepBot","nick") else "RepBot"
	realname = cfg.get("RepBot","realname") if cfg.has_option("RepBot","realname") else "Reputation Bot"
	factory = RepBotFactory(channel, cfg, nickname=nickname, realname=realname)
	print "Connecting to {0}:{1}\t{2}".format(server,port,channel)
	if cfg.has_option("RepBot","ssl") and cfg.getboolean("RepBot","ssl"):
		print "Using SSL"
		reactor.connectSSL(server, port, factory, ssl.ClientContextFactory())
	else:
		print "Not using SSL"
		reactor.connectTCP(server, port, factory)
	reactor.run()


