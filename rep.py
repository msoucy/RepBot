import xchat
import operator

# TODO: Forcing a print resets the timer
# TODO: Change it to use the Context system
## This means that it will always print to the channel it's init'd to
# TODO: Detect renames
# TODO: Tell people who are ignored that they ARE ignored

__module_name__ = "Rep System"
__module_version__ = "0.6"
__module_description__ = "Keep a record of user reputations"

reps={}
ignorelist=set()
report_time = 1000*60*60
autorespond=False
privmsg=False
	
def parseName(name):
	name = name[:-2].strip()
	return name

def get_rep(name):
	return reps.get(name,0)

def incr_rep(name):
	global reps
	reps[name]=reps.get(name,0)+1

def decr_rep(name):
	global reps
	reps[name]=reps.get(name,0)-1

def dump_rep():
	fi = open("reps.txt","w")
	fi.write(str(reps))
	fi.close()
	
def is_rep_cmd(s):
	return (s.startswith(("!rep", "!help")) or s.endswith(("++","--")))



def rep_admin_cb(word, word_eol, userdata):
	global reps, ignorelist, reporter, autorespond, privmsg
	if xchat.get_info("nick") is None:
		print "Yo, you're not connected"
		return
	if len(word) == 1:
		# Get a quick, private view of the current reps
		print reps
	elif word[1] == "clearall":
		reps = {}
	elif word[1] == "clear":
		for name in word[2:]:
			reps.pop(name.strip(),None)
	elif word[1] == "dump":
		dump_rep()
	elif word[1] == "ignore":
		ignorelist |= set(word[2:])
	elif word[1] == "unignore":
		ignorelist -= set(word[2:])
	elif word[1] == "ignorelist":
		print list(ignorelist)
	elif word[1] == "set" and len(word)==4:
		reps[word[2].strip()] = int(word[3].strip())
	elif word[1].startswith("apply"):
		reps.update(eval(word_eol[2]))
	elif word[1] == "all" and len(reps):
		xchat.command("msg {0} All reps: {1}".format(xchat.get_info("channel"),reps))
	elif word[1] == "report" and len(word)==3:
		if word[2] == "on" and not reporter:
			reporter = xchat.hook_timer(report_time, report_cb)
		elif word[2] == "off" and reporter:
			xchat.unhook(reporter)
		elif word[2] == "now":
			report_cb(None)
			xchat.unhook(reporter)
			reporter = xchat.hook_timer(report_time, report_cb)
	elif word[1] == "private" and len(word)==3:
		privmsg = (word[2] == "on")
	elif word[1] == "tell" and len(word)==3:
		xchat.command("msg {0} Rep for {1}: {2}".format(xchat.get_info('channel'),word[2],get_rep(word[2])))
	elif word[1] == "auto" and len(word)==3:
		autorespond = (word[2] == "on")
		print "Autorespond changed to {0}".format(autorespond)
	else:
		print "Invalid rep admin command"
	return xchat.EAT_ALL

def process_rep_cmd(uname, msg, source):
	# uname is the name of the person who says it
	# msg is !rep or the name++/--
	print source
	if msg.endswith(('++','--')):
		if parseName(msg) != uname:
			if msg.endswith("++"):
				name = parseName(msg)
				if ' ' not in name:
					incr_rep(name)
			elif msg.endswith("--"):
				name = parseName(msg)
				if ' ' not in name:
					decr_rep(name)
	elif msg.startswith("!rep"):
		msg=msg[len("!rep"):].strip()
		name = msg if msg else uname
		xchat.command("msg {0} Rep for {1}: {2}".format(uname,name,get_rep(name)))
	elif msg.startswith("!ver"):
		xchat.command('msg {0} I am RepBot version {1}'.format(uname,__module_version__))
	elif msg.startswith("!help"):
		xchat.command('msg {0} Message me with "!rep <name>" to get the reputation of <name>'.format(uname))
		xchat.command('msg {0} Message me with "<name>++" or "<name>--" to change the reputation of <name>. You are not able to change your own rep.'.format(uname))
		xchat.command('msg {0} Message me with "!version" to see my version number'.format(uname))
	elif autorespond and source == xchat.get_info('name'):
		#xchat.command('msg {0} Enter "!help" for usage.'.format(uname,__module_version__))
		#print xchat.get_info("channel")
		pass

def rep_cb(word, word_eol, userdata):
	if xchat.get_info("nick") is None:
		print "Yo, you're not connected"
	else:
		msg = word_eol[3][1:]
		name = word[0][1:word[0].find('!')]
		if name in ignorelist:
			xchat.command("msg {0} You have been blocked from utilizing my functionality.".format(name))
		elif name != xchat.get_info('nick'):
			if privmsg:
				if word[2] == xchat.get_info("nick"):
					process_rep_cmd(name,msg, word[2])
				elif word[2].startswith('#') and is_rep_cmd(msg):
					xchat.command("msg {0} I only respond to private messages".format(name))
			else:
				process_rep_cmd(name, msg, word[2])
	return xchat.EAT_NONE

def report_cb(userdata, cached=[None,None]):
	sorted_reps = list(reversed(sorted(reps.iteritems(), key=operator.itemgetter(1))))
	highest = sorted_reps[:5]
	lowest = sorted_reps[-5:]
	if highest != cached[0]:
		xchat.command("msg {0} Top reps: {1}".format(xchat.get_info("channel"),highest))
		cached[0] = highest
	if lowest != cached[1]:
		xchat.command("msg {0} Bottom reps: {1}".format(xchat.get_info("channel"),lowest))
		cached[1] = lowest
	return True

def __init__():
	global reps
	print "Loaded reputation system v"+__module_version__
	try:
		reps = eval(open("reps.txt").read())
	except SyntaxError:
		print "Error: could not read reputation file. Contents: `{0}`".format(open("reps.txt").read())
	except IOError:
		print "Error: could not open reputation file"

def __del__(userdata):
	dump_rep()
	print "Unloaded reputation system!"
	

# Do rep stuff
xchat.hook_command("REP", rep_admin_cb, help="/REP admin commands")
xchat.hook_server("PRIVMSG", rep_cb)
reporter = xchat.hook_timer(report_time, report_cb)

__init__()
xchat.hook_unload(__del__)

