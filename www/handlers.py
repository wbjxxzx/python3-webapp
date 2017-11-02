#!/usr/bin/env python3
#-*- coding:utf-8 -*-
__author__ = 'Ming'

from asyncweb import get
from models import User
@get('/')
def index(request):
    users = yield from User.findAll()
    return {
        '__template__': 'test.html',
        'users': users
    }

@get('/hello')
def hello(request):
    return '<h1>hello</h1>'