#!/usr/bin/python

from .backend_yaml import ReputationSystemYAML
from .config import Config
from .ReputationBot import ReputationBot
from .TwistedIRCBot import TwistedIRCModule

if __name__ == "__main__":
    cfg = Config("data/settings.txt")
    bot = ReputationBot(ReputationSystemYAML(cfg.reps))
    mod = TwistedIRCModule(cfg, bot)
    mod.start()
