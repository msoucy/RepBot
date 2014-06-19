# Module system
# Components can register with the module system
# Admin commands go through this
# Also provides the mapping of frontends to backends

from .interfaces import Frontend
from fuf import ActionSet

class Modules(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super(Modules, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self._types = {}
        self._modules = {}
        self._backends = {}

    def register(self, tname, t):
        if tname in self._types:
            raise KeyError("{} already in module type registry".format(tname))
        self._types[tname] = t

    def create(self, name, tname, cfg):
        if tname not in self._types:
            raise KeyError("{} not in module type registry".format(tname))
        modtype = self._types[tname]
        if issubclass(modtype, Frontend):
            mod = modtype(cfg, self.get(cfg.backend))
        else:
            mod = modtype(cfg)
        self._modules[name] = mod

    def get(self, name):
        if name in self._modules:
            return self._modules[name]
        elif name in self._backends:
            return self._backends[name]
        raise KeyError("{} not in module registry".format(name))

    __getitem__ = get

def Module(modname=None):
    class _ModuleMetaClass(type):
        def __new__(cls, name, bases, attrs):
            cls = type.__new__(cls, name, bases, dict(attrs, action=ActionSet()))
            Modules().register(modname or name, cls)
            return cls
    return _ModuleMetaClass('Module', (object, ), {})

def Frontend(modname=None):
    class _Module(Module(modname)): pass

