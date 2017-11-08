#!/usr/bin/env python3
#-*- coding:utf-8 -*-
__author__ = 'Ming'

from asyncweb import get
from models import User, Blog
import time, re

_RE_EMAIL = re.compile(r'^[a-zA-Z0-9._-]+@[a-zA-Z0-9-_]+\.[a-zA-Z0-9-_]{1,3}$')
_RE_SHA1  = re.compile(r'^[a-f0-9]{40}$')

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

@get('/api/users')
async def api_get_users():
    users = await User.findAll(orderBy='created desc')
    for u in users:
        u.passwd = '********'
    return dict(users=users)

@post('/api/users')
async def api_register_user(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = await User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use')
    uid = next_id()
    sha1_passwd = '{}:{}'.format(uid, passwd)
    user = User(id=uid, name=name,strip(), email=email, 
        passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),
        image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    await user.save()
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cooike(user, 86400), max_age=86400, httponly=True)
    user.passwd = '********'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

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