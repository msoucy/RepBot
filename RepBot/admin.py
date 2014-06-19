#!/usr/bin/python

from ast import literal_eval
import json
import re
from fuf import ActionSet
from twisted.internet import reactor
from twisted.internet.task import LoopingCall

def get_channel_arg(channel, args):
    if args and args[0].startswith(('#', '&', '+', '!')):
        channel = args.pop(0)
    return channel


Action = ActionSet("Action_")



@Action
def Action_help(bot, user, *cmds):
    """List command help"""
    if cmds:
        for cmds in cmds:
            a = Action[arg]
            if a:
                bot.send_to(user, "{0.name}:\t{0.helpmsg}".format(a))
    else:
        bot.send_to(user, " ".join(a for a in Action))


@Action
def Action_verify(bot, user):
    """Confirm admin access"""
    bot.send_to(user, "Authentication valid")


@Action
def Action_admin(bot, user, cmd, *args):
    """Adjust user admin access"""
    if cmd == "list":
        bot.send_to(user, str(list(bot.cfg["admins"])))
    elif not args:
        bot.send_to(user, "Admin change failed: too few arguments")
    elif cmd == "add":
        bot.cfg["admins"] = sorted(set(bot.cfg["admins"]) | set(args))
    elif cmd in ("remove", "rm"):
        bot.cfg["admins"] = sorted(set(bot.cfg["admins"]) - set(args))
    else:
        bot.send_to(user, "Admin change failed: unknown action")
    bot.rebuild_wildcards()


@Action
def Action_ignore(bot, user, cmd, *args):
    """Adjust ignore list"""
    if cmd == "list":
        bot.send_to(user, str(list(bot.cfg["ignores"])))
    elif not args:
        bot.send_to(user, "Admin change failed: too few arguments")
    elif cmd == "add":
        bot.cfg["ignores"] = sorted(set(bot.cfg["ignores"]) | set(args))
    elif cmd in ("remove", "rm"):
        bot.cfg["ignores"] = sorted(set(bot.cfg["ignores"]) - set(args))
    else:
        bot.send_to(user, "Ignore change failed: unknown action")
    bot.rebuild_wildcards()

@Action
def Action_cfg(bot, user, setting, *args):
    """Control a config setting"""
    if args:
        bot.send_to(user, "{0} = {1}".format(setting, bot.cfg.get(setting)))
    elif len(args) == 1:
        newval = literal_eval(args[1])
        if type(newval) == type(bot.cfg.get(setting)):
            bot.cfg[setting] = newval
        # I know, a sad little hack for now.
        if setting == "savespeed":
            bot.saver.stop()
            bot.saver.start(newval)
    elif setting == "report" and len(args) == 2:
        newval = literal_eval(args[1])
        if type(newval) == type(bot.cfg["report"].get(args[0])):
            bot.cfg["report"][args[0]] = newval
    else:
        bot.send_to(user, "Invalid config setting change")

@Action
def Action_dump(bot, user):
    bot.reps.save()
    bot.log("Rep file dumped")


@Action
def Action_save(bot, user):
    """Save all bot information"""
    bot.save()


@Action
def Action_load(bot, user):
    """Load database from a file"""
    bot.reps.load()
    bot.log("Rep file loaded")


@Action
def Action_filter(bot, user):
    """Remove unused entries"""
    bot.reps.filter()
    bot.log("Filtered zeroed entries")


@Action
def Action_clear(bot, user, *args):
    """Remove the given names from the system"""
    if args == ["all"]:
        bot.reps.reps = {}
    else:
        for name in args:
            bot.reps.set(name, 0)


@Action
def Action_tell(bot, user, *args):
    """Tell a channel rep information for users"""
    user = get_channel_arg(user, args)
    for name in args:
        bot.send_to(user, bot.reps.tell(name))


@Action
def Action_all(bot, user, dest=None):
    """Get all reputations"""
    dest = dest or user
    bot.send_to(user, bot.reps.all())


@Action
def Action_limit(bot, user, cmd, *args):
    """Adjust limits"""
    if len(args) < 2:
        bot.send_to(user, "Limit change failed: too few arguments")
        return
    if cmd == "rep":
        if args:
            bot.cfg["replimit"] = int(args[0])
        else:
            bot.send_to(user, "Rep limit: {0}".format(bot.cfg["replimit"]))
    elif cmd == "time":
        if args:
            bot.cfg["timelimit"] = int(args[0])
        else:
            bot.send_to(user, "Time limit: {0}".format(bot.cfg["timelimit"]))
    else:
        bot.send_to(user, "Limit change failed: unknown limit")


@Action
def Action_set(bot, user, nick, value):
    """Manually set a user's rep value"""
    bot.bot.repsys.set(nick, int(value))


@Action
def Action_allow(bot, user, *args):
    """Clear rep timeout restrictions for all given users"""
    for name in args:
        bot.users[name] = []


@Action
def Action_term(bot, user, *msg):
    """Safely terminate"""
    bot.save()
    for chan in bot.cfg["channels"]:
        bot.leave(chan, " ".join(msg))
    bot.quit(" ".join(msg))
    reactor.stop()


@Action
def Action_join(bot, user, *chans):
    """Join a channel"""
    for chan in chans:
        bot.join(chan)
        bot.cfg["channels"].append(chan)
    bot.cfg["channels"] = sorted(set(bot.cfg["channels"]))


@Action
def Action_part(bot, user, *chars):
    """Leave a channel"""
    for chan in chars:
        bot.leave(chan)
        bot.cfg["channels"].remove(chan)

@Action
def Action_autoreport(bot, user, args):
    """Automatically report to a channel"""
    channels = bot.cfg["report"]["channels"]
    for chan in args:
        if chan in bot.loops:
            bot.loops.pop(chan).stop()
            channels.remove(chan)
        else:
            bot.loops[chan] = LoopingCall(lambda:bot.report(chan))
            bot.loops[chan].start(bot.cfg["report"]["delay"])
            channels.append(chan)

@Action
def Action_report(bot, user, dest=None):
    """Generate a report"""
    bot.send_to(dest or user, bot.reps.report())

@Action
def Action_as(bot, user, fakeuser, *cmd):
    """Spoof a message as a user"""
    if not cmd:
        bot.send_to(user, "as failed: Not enough information")
    else:
        bot.privmsg(fakeuser,fakeuser," ".join(cmd))

@Action
def Action_say(bot, user, dest, *msg):
    """Say a message"""
    if not msg:
        bot.send_to(user, "Not enough arguments")
    bot.send_to(dest, " ".join(msg))

class get_command(object):
    def __init__(self):
        self.reg = re.compile(r'^(@|(?:admin\s+))(?:!(?P<module>[a-zA-Z_]\w*))?\s*(?P<cmd>\S+)\s*(?P<args>.*)$')
    def __call__(self, msg):
        mat = self.reg.match(msg)
        if mat:
            return mat.groupdict()
        return None
get_command = get_command()

def admin(bot, user, command):
    cmd = command["cmd"]
    args = command["args"]
    if cmd in Action:
        try: Action[cmd](bot, user, *(args.split()))
        except:
            bot.send_to(user, "Can't run that admin command with arguments: {}".format(args.split()))
            raise
    else:
        print "Invalid command {0}".format(command)

