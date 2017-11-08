#!/usr/bin/env python3
#-*- coding:utf-8 -*-
__author__ = 'Ming'

from asyncweb import get, post
from models import *
from apis import APIError, APIValueError, APIPermissionError
from aiohttp import web
import time, re, hashlib, json, logging
from conf.config import configs 

_RE_EMAIL = re.compile(r'^[a-zA-Z0-9._-]+@[a-zA-Z0-9-_]+\.[a-zA-Z0-9-_]{1,3}$')
_RE_SHA1  = re.compile(r'^[a-f0-9]{40}$')
COOKIE_NAME = 'pyblog'
_COOKIE_KEY = configs.session.secret

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

@get('/register')
def register(request):
    return {
        '__template__': 'register.html',
    }

@get('/signin')
def signin(request):
    return {'__template__': 'signin.html'}

@get('/signout')
def singout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-delete-', max_age=0, httponly=True)
    logging.info('user signed out.')
    return r

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
    user = User(id=uid, name=name.strip(), email=email, 
        passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),
        image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    await user.save()
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cooike(user, 86400), max_age=86400, httponly=True)
    user.passwd = '********'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

@post('/api/authenticate')
async def authenticate(*, email, passwd):
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid password.')
    users = await User.findAll('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0]
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid password.')
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cooike(user, 86400), max_age=86400, httponly=True)
    user.passwd = '********'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

async def user2cooike(user, max_age):
    expires = str(int(time.time() + max_age))
    s = '{}-{}-{}-{}'.format(user.id, user.passwd, expires, _COOKIE_KEY)
    return '-'.join([user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()])

async def cookie2user(cookie_str):
    ''' Parse cookie and load user if cookie is valid '''
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = '{}-{}-{}'.format(uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '********'
        return user 
    except Exception as e:
        logging.exception(e)
        return None

def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()

@get('/api/blogs')
async def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, blogs=())
    blogs = await Blog.findAll(orderBy='created desc')
    return dict(page=p, blogs=blogs)

@get('/manage/blogs')
def manage_blogs(*, page='1'):
    return {
        '__template__': 'manage_blogs.html',
        'page_index': get_page_index(page),
    }

@post('/api/blogs')
async def api_create_blog(request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image,
        name=name.strip(), summary=summary.strip(), content=content.strip())
    await blog.save()
    return blog

def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    return p if p >= 1 else 1

def text2html(text):
    lines = map(lambda s:'<p>{}</p>'.format(s).
            replace('&', '&amp;').
            replace('<', '&lt;').
            replace('>', '&gt;'),
            filter(lambda s: s.strip() != '', text.split('\n'))
    )
    return ''.join(lines)

@get('/blog/{id}')
async def get_blog(id):
    blog = await Blog.find(id)
    comments = await Comment.findAll('blog_id=?', [id], orderBy='created desc')
    for c in comments:
        c.html_content = text2html(c.content)
    blog.html_content = blog.content
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments,
    }

@get('/api/blogs/{id}')
async def api_get_blog(*, id):
    blog = await Blog.find(id)
    return blog

@get('/manage/blogs/create')
def manage_create_blog():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs',
    }