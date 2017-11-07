#!/usr/bin/env python3
#-*- coding:utf-8 -*-
__author__ = 'Ming'

from asyncweb import get
from models import User, Blog
import time

@get('/')
def index(request):
    summary = 'something interesting'
    blogs = [
        Blog(id='1', name='test blog', summary=summary, created=time.time()-120),
        Blog(id='2', name='Something New', summary=summary, created=time.time()-3600),
        Blog(id='3', name='learn python', summar=summary, created=time.time()-7200),
    ]
    return {
        '__template__': 'blogs.html',
        'blogs': blogs,
    }

@get('/login')
def login(request):
    return {'__template__': 'login.html'}

@get('/test')
async def test(request):
    users = await User.findAll()
    return {
        '__template__': 'test.html',
        'users': users
    }

@get('/hello')
def hello(request):
    return '<h1>hello</h1>'