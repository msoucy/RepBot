#!/usr/bin/python

import sys, json, time
from twisted.words.protocols import irc
from twisted.internet import protocol, reactor, ssl
from repsys import ReputationSystem
import admin

def getNameFromIdent(name):
	return name.partition("!")[0]

class RepBot(irc.IRCClient):
	
	def __init__(self, cfg):
		self.version = "0.8.0"
		self.reps = ReputationSystem(cfg.get("reps", "data/reps.txt"))
		self.ignorelist = set(cfg.get("ignore", []))
		self.admins = set(cfg.get("admins",[]))
		self.privonly = False
		self.autorespond = False
		self.replimit = (cfg.get("replimit", 5))
		self.timelimit = (cfg.get("timelimit", 60.0*60.0))
		
		self.nickname = cfg.get("nick", "RepBot")
		self.realname = cfg.get("realname", "Reputation Bot")
		self.servername = cfg.get("servname", "Reputation Bot")
		self.users={}

	def signedOn(self):
		print "Signed on as {0}.".format(self.nickname)
		for chan in cfg.get("channels",[]):
			self.join(chan)

	def joined(self, channel):
		print "Joined {0}.".format(channel)
	
	def admin(self, user, msg):
		admin.admin(self, user, msg)
	
	def repcmd(self, user, channel, msg):
		def parseName(name): return name[:-2].strip()
		# Respond to private messages privately
		if channel == self.nickname: channel = user
		
		args = msg.split()
		cmd = args[0] if args else ""
		args = args[1:] if args else []
		
		if len(args) == 0 and cmd.endswith(('++','--')) and parseName(cmd) != user:
			currtime = time.time()
			self.users[user] = [val for val in self.users.get(user,[]) if (currtime-val)<self.timelimit]
			if len(self.users[user]) < self.replimit:
				name = parseName(cmd)
				if cmd.endswith("++"):
					self.reps.incr(name)
					self.users[user].append(time.time())
				elif cmd.endswith("--"):
					self.reps.decr(name)
					self.users[user].append(time.time())
			else:
				self.msg(user, "You have reached your rep limit. You can give more rep in {0} seconds"
								.format(int(self.timelimit-(currtime-val))))
			return
		if cmd.startswith("rep"):
			self.msg(channel, self.reps.tell(args[0] if args else user))
		elif cmd.startswith("ver"):
			self.msg(channel, 'I am RepBot version {0}'.format(self.version))
		elif cmd.startswith("help"):
			self.msg(channel, 'Message me with "!rep <name>" to get the reputation of <name>')
			self.msg(channel, 'Say "<name>++" or "<name>--" to change the reputation of <name>. You are not able to change your own rep.')
			self.msg(channel, 'Message me with "!version" to see my version number')
		elif self.autorespond and channel == user:
			# It's not a valid command, so let them know
			# Only respond privately
			self.msg(user, 'Invalid command. MSG me with !help for information')

	def privmsg(self, user, channel, msg):
		if not user: return
		user = getNameFromIdent(user)
		
		if channel != self.nickname:
			if msg.startswith(self.nickname+":"): msg = msg[len(self.nickname)+1:].strip()
			elif msg.startswith('!'): msg = msg[1:]
			elif not msg.endswith(("++","--")): return
		elif msg.startswith('!'): msg = msg[1:]

		if user in self.ignorelist:
			self.msg(user, "You have been blocked from utilizing my functionality.")
		elif channel == self.nickname:
			# It's a private message
			if msg.startswith("admin"):
				if user in self.admins:
					self.admin(user, msg.replace("admin","",1).strip())
				else:
					self.log("Admin attempt from "+user)
					self.msg(user, "You are not an admin.")
			else:
				self.repcmd(user, channel, msg)
		elif not self.privonly:
			# I'm just picking up a regular chat
			# And we aren't limited to private messages only
			self.repcmd(user, channel, msg)
	
	def log(self, msg):
		print time.asctime(),msg


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
	cfg = json.load(open("data/settings.txt"))
	server = cfg.get("server","")
	port = cfg.get("port",6667)
	factory = RepBotFactory(cfg)
	print "Connecting to {0}:{1}".format(server,port)
	if cfg.get("ssl", False):
		print "Using SSL"
		reactor.connectSSL(server, port, factory, ssl.ClientContextFactory())
	else:
		print "Not using SSL"
		reactor.connectTCP(server, port, factory)
	reactor.run()


