#!/usr/bin/python

import yaml
import os.path

class Config(object):

    def __init__(self, filename):
        self._filename = filename
        self._data = {}
        self.load()

    def __getitem__(self, name):
        return self._data[name]

    def __getattr__(self, name):
        if name.startswith('_'):
            return super(Config, self).__getattr__(name, value)
        else: return self._data[name]

    def __setitem__(self, name, value):
        self._data[name] = value 
        return self._data[name]

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super(Config, self).__setattr__(name, value)
            return
        self._data[name] = value 
        return self._data[name]

    def save(self):
        with open(self._filename, "w") as fi:
            yaml.dump(self._data, fi, default_flow_style=False)

    def load(self):
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
            "spy": False,
            "report": {
                "channels": [],
                "delay": 60*60
            },
            "savespeed": 3*60*60,
            "topprivate": True
        }
        # Add the new stuff
        if os.path.exists(self._filename):
            ret.update(yaml.safe_load(open(self._filename)))
        # Fix set information
        ret["ignore"] = sorted(set(ret["ignore"]))
        ret["admins"] = sorted(set(ret["admins"]))
        ret["report"]["channels"] = sorted(set(ret["report"]["channels"]))
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
        self._data = cleanup(ret)
        # Write the full config file, so they have a full listing
        self.save()
