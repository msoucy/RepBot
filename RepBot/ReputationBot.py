#!/usr/bin/python
from __future__ import print_function

import yaml
import time
import re

from repcmds import get_rep_change
import admin

class ReputationBot:

    def __init__(self, repsys):
        self.version = "0.13.0"
        self.repsys = repsys

    def log(self, msg):
        print(time.asctime(), msg)

    def save(self):
        self.repsys.save()

    def handle(self, frontend, user, changer):
        name = changer.getUser()
        if name == frontend.canonical_name(user):
            frontend.send_to(user, "Cannot change own rep")
        else:
            self.repsys.apply(changer)

    def admin(self, source, cmd):
        admin.admin(self, source, cmd)

    def repcmd(self, frontend, source, msg, replyto=None):

        replyto = replyto or source

        args = msg.split()
        cmd, args = (args[0], args[1:]) if args else ("",[])
        changer = get_rep_change(msg)
        send = lambda msg: frontend.send_to(replyto, msg)

        if changer:
            frontend.handle(source, changer)
        elif cmd in ("rep",):
            name = frontend.canonical_name(args[0] if args else source)
            send("Rep for {0}: {1}".format(name, self.repsys.get(name)))
        elif cmd in ("top", "report"):
            send(self.repsys.report())
        elif cmd in ("ver", "version", "about"):
            send('I am RepBot version {0}'.format(self.version))
        elif cmd in ("help",):
            frontend.send_help(replyto)
        elif source == replyto:
            # It's not a valid command, so let them know
            # Only respond privately
            send('Invalid command. MSG me with !help for information')
