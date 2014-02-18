#!/usr/bin/python

from ast import literal_eval
import json
from twisted.internet import reactor
from twisted.internet.task import LoopingCall

def get_channel_arg(channel, args):
    if args and args[0].startswith(('#', '&', '+', '!')):
        channel = args.pop(0)
    return channel


adminActions = {}


def Action(name, helpmsg):
    class ActionClass(object):
        __slots__ = ('name', 'helpmsg', 'cmd')

        def __init__(self, f):
            self.name = name
            self.helpmsg = helpmsg
            self.cmd = f
            adminActions[name] = self

        def __call__(self, *args, **kwargs):
            return self.cmd(*args, **kwargs)
    return ActionClass


@Action("help", "List command help")
def Action_help(bot, user, args):
    if args:
        for arg in args:
            a = adminActions.get(arg)
            if a:
                bot.send_to(user, "{0}:\t{1}".format(a.name, a.helpmsg))
    else:
        bot.send_to(
            user,
            " ".join(a for a in adminActions))


@Action("verify", "Confirm admin access")
def Action_verify(bot, user, args):
    bot.send_to(user, "Authentication valid")


@Action("admin", "Adjust user admin access")
def Action_admin(bot, user, args):
    if len(args) < 2 and args[0] != "list":
        bot.send_to(user, "Admin change failed: too few arguments")
        return
    cmd = args[0]
    args = args[1:]
    if cmd == "add":
        bot.cfg["admins"] = sorted(set(bot.cfg["admins"]) | set(args))
    elif cmd in ("remove", "rm"):
        bot.cfg["admins"] = sorted(set(bot.cfg["admins"]) - set(args))
    elif cmd == "list":
        bot.send_to(user, str(list(bot.cfg["admins"])))
    else:
        bot.send_to(user, "Admin change failed: unknown action")
    bot.rebuild_wildcards()


@Action("ignore", "Adjust ignore list")
def Action_ignore(bot, user, args):
    if len(args) < 1:
        bot.send_to(user, "Ignore change failed: too few arguments")
        return
    cmd = args[0]
    args = args[1:]
    if cmd == "add":
        bot.cfg["ignore"] = sorted(set(bot.cfg["ignore"]) | set(args))
    elif cmd in ("remove", "rm"):
        bot.cfg["ignore"] = sorted(set(bot.cfg["ignore"]) - set(args))
    elif cmd == "list":
        bot.send_to(user, str(list(bot.cfg["ignore"])))
    else:
        bot.send_to(user, "Ignore change failed: unknown action")
    bot.rebuild_wildcards()

@Action("cfg", "Control a config setting")
def Action_cfg(bot, user, args):
    if len(args) == 1:
        bot.send_to(user, "{0} = {1}".format(args[0], bot.cfg.get(args[0])))
    elif len(args) == 2:
        newval = literal_eval(args[1])
        if type(newval) == type(bot.cfg.get(args[0])):
            bot.cfg[args[0]] = newval
        # I know, a sad little hack for now.
        if args[0] == "savespeed":
            bot.saver.stop()
            bot.saver.start(newval)
    elif args[0] == "report" and len(args) == 3:
        newval = literal_eval(args[2])
        if type(newval) == type(bot.cfg["report"].get(args[1])):
            bot.cfg["report"][args[1]] = newval
    else:
        bot.send_to(user, "Invalid config setting change")

@Action("dump", "Dump database to a file")
def Action_dump(bot, user, args):
    bot.reps.save()
    bot.log("Rep file dumped")


@Action("save", "Save all bot information")
def Action_save(bot, user, args):
    bot.save()


@Action("load", "Load database from a file")
def Action_load(bot, user, args):
    bot.reps.load()
    bot.log("Rep file loaded")


@Action("filter", "Remove unused entries")
def Action_filter(bot, user, args):
    bot.reps.filter()
    bot.log("Filtered zeroed entries")


@Action("clear", "Remove the given names from the system")
def Action_clear(bot, user, args):
    if len(args) == 1 and args[0] == "all":
        bot.reps.reps = {}
    else:
        for name in args:
            bot.reps.set(name, 0)


@Action("tell", "Tell a channel rep information for users")
def Action_tell(bot, user, args):
    user = get_channel_arg(user, args)
    for name in args:
        bot.send_to(user, bot.reps.tell(name))


@Action("all", "Get all reputations")
def Action_all(bot, user, args):
    user = get_channel_arg(user, args)
    bot.send_to(user, bot.reps.all())


@Action("limit", "Adjust limits")
def Action_limit(bot, user, args):
    if len(args) < 2:
        bot.send_to(user, "Limit change failed: too few arguments")
        return
    cmd = args[0]
    args = args[1:]
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


@Action("set", "Manually set a user's rep value")
def Action_set(bot, user, args):
    if len(args) != 2:
        bot.send_to(user, "Set failed: incorrect number of arguments")
    else:
        bot.reps.set(args[0], args[1])


@Action("allow", "Clear rep timeout restrictions for all given users")
def Action_allow(bot, user, args):
    for name in args:
        bot.users[name] = []


@Action("apply", "Apply the Python dictionary provided to the rep database")
def Action_apply(bot, user, args):
    bot.reps.update(json.loads(" ".join(args)))

@Action("term", "Safely terminate RepBot")
def Action_term(bot, user, args):
    bot.save()
    for chan in bot.cfg["channels"]:
        bot.leave(chan, " ".join(args))
    bot.quit(" ".join(args))
    reactor.stop()


@Action("join", "Join a channel")
def Action_join(bot, user, args):
    for chan in args:
        bot.join(chan)
        bot.cfg["channels"].append(chan)
    bot.cfg["channels"] = sorted(set(bot.cfg["channels"]))


@Action("part", "Leave a channel")
def Action_part(bot, user, args):
    for chan in args:
        bot.leave(chan)
        bot.cfg["channels"].remove(chan)

@Action("autoreport", "Automatically report to a channel")
def Action_autoreport(bot, user, args):
    channels = bot.cfg["report"]["channels"]
    for chan in args:
        if chan in bot.loops:
            bot.loops.pop(chan).stop()
            channels.remove(chan)
        else:
            bot.loops[chan] = LoopingCall(lambda:bot.report(chan))
            bot.loops[chan].start(bot.cfg["report"]["delay"])
            channels.append(chan)

@Action("report", "Generate a report")
def Action_report(bot, user, args):
    user = get_channel_arg(user, args)
    if args:
        bot.send_to(user, "Report failed: Too many arguments")
    else:
        bot.send_to(user, bot.reps.report())

@Action("as", "Spoof a message as a user")
def Action_as(bot, user, args):
    if len(args)<2:
        bot.send_to(user, "as failed: Not enough information")
    else:
        bot.privmsg(args[0],args[0]," ".join(args[1:]))

@Action("say", "Say a message")
def Action_say(bot, user, args):
    if len(args) < 2:
        bot.send_to(user, "Not enough arguments")
    bot.send_to(args[0], " ".join(args[1:]))

def admin(bot, user, msg):
    if not msg.strip():
        return
    command = msg.split()[0].lower()
    args = msg.split()[1:]
    action = adminActions.get(command)
    if action:
        action(bot, user, args)
    else:
        print "Invalid command {0}".format(command)

