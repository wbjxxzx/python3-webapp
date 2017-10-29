#!/usr/bin/env python3
#-*- coding:utf-8 -*-
__author__ = 'Ming'

import functools, os, logging
import asyncio

def handle_request(path, *, method):
    ''' define decorator @get('/path') '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = method
        wrapper.__route__  = path
        return wrapper
    return decorator

'''
def post(path):
    ''' define decorator @post('/path') '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__  = path
        return wrapper
    return decorator
'''

get = functools.partial(handle_request, method='GET')
put = functools.partial(handle_request, method='PUT')
post = functools.partial(handle_request, method='POST')
delete = functools.partial(handle_request, method='DELETE')

def add_route(app, fn):
    method = getattr(fn, '__method__', None)
    path   = getattr(fn, '__route__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in {}'.format(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info('add route {} {} => {}({})'.format(method, path, fn.__name__,
        ', '.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn))

def add_routes(app, module_name):
    n = module_name.rfind('.')
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n+1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)

def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logging.info('add static {} => {}'.format('/static/', path))


class RequestHandler(object):
    '''
    # RequestHandler目的就是从URL函数中分析其需要接收的参数，从request中获取必要的参数，
    # URL函数不一定是一个coroutine，因此我们用RequestHandler()来封装一个URL处理函数。
    # 调用URL函数，然后把结果转换为web.Response对象，这样，就完全符合aiohttp框架的要求
    '''
    def __init__(self, app, fn):
         self._app = app
         self._func = fn

    async def __call__(self, request):
        # 任何类，只需要定义一个__call__()方法，就可以直接对实例进行调用
        kw = None
        r = await self._func(**kw)
        return r
