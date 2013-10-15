#!/usr/bin/python

import re
import random

def canonical_name(user):
    return re.split(r"[\|`:_]", user.strip())[0].lower()

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

class MIPSRepChange(RepChangeCommand):
    def __init__(self, msg):
        super(MIPSRepChange, self).__init__()

        m = msg.lower().split()

        if len(m) != 3 or m[0] != "addi" or m[2] not in ("+1","1","-1"):
            return

        self.setUser(m[1])
        self.setValid(True)
        self.op = ('+'+m[2])[-2:]

    def perform(self, val):
        if self.op == "+1":
            return val + 1
        elif self.op == "-1":
            return val - 1

def get_rep_change(msg):
    commands = [
        PrePostfixRepChange,
        GPlusRepChange,
        X86_64RepChange,
        X86_32RepChange,
        X86_16RepChange,
        X86_8RepChange,
        PDP8RepChange,
        MIPSRepChange
    ]

    for changer in commands:
        c = changer(msg)
        if c.isValid():
            return c
    return None

