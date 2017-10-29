#!/usr/bin/env python3
#-*- coding:utf-8 -*-
__author__ = 'Ming'

from coroweb import get
@get('/')
def index(request):
    return '<h1>Welcome</h1>'

@get('/hello')
def hello(request):
    return '<h1>hello</h1>'