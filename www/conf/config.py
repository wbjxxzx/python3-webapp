#!/usr/bin/env python3
#-*- coding:utf-8 -*-
__author__ = 'Ming'

from . import config_default

class Mydict(dict):
    ''' simple dict support access as x.y style '''
    def __init__(self, names=(), values=(), **kw):
        super(Mydict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError("'Dict' object has no attribute: {}".format(key))
    
    def __setattr__(self, key, value):
        self[key] = value

def merge(defaults, override):
    r = {}
    for k, v in defaults.items():
        if k in override:
            if isinstance(v, dict):
                r[k] = merge(v, override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r

def toMydict(d):
    my = Mydict()
    for k, v in d.items():
        my[k] = toMydict(v) if isinstance(v, dict) else v
    return my

configs = config_default.configs

try:
    import config_production
    configs = merge(configs, config_production)
except ImportError:
    pass

configs = toMydict(configs)