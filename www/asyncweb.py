#!/usr/bin/env python3
#-*- coding:utf-8 -*-
__author__ = 'Ming'

''' 重构coroweb '''

import asyncio, functools, inspect, logging, os
from aiohttp import web
from apis import APIError

# 工厂模式，生成GET POST 等方法的装饰器
def handle_request(path, *, method):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = method
        wrapper.__route__  = path
        return wrapper
    return decorator

get  = functools.partial(handle_request, method='GET')
post = functools.partial(handle_request, method='POST')
put  = functools.partial(handle_request, method='PUT')
delete = functools.partial(handle_request, method='DELETE')

''' 
RequestHandler 目的是从URL处理函数中分析其需要接收的参数，从request中获取必要的参数
URL处理函数不一定是一个coroutine，因此我们用RequestHandler()来封装一个URL处理函数
调用URL处理函数，然后把结果转换为web.Response对象，这样就符合aiohttp的要求
'''
class RequestHandler(object):
    def __init__(self, func):
        self._func = asyncio.coroutine(func)

    # 任何类，只需要定义一个__call__()方法，就可以直接对实例进行调用
    async def __call__(self, request):
        # 获取URL处理函数的参数
        url_args = inspect.signature(self._func).parameters
        logging.info('{} args: {}'.format(self._func.__name__, url_args))
        
        # 获取从GET或POST传入的参数，如果URL处理函数有这参数名，就加入dict
        kw = {arg: value for arg, value in request.__data__.items() if arg in url_args}

        # 获取 match_info 的参数值，例如 @get('/blog/{id}') 之类的参数
        kw.update(request.match_info)
        
        # 如果有 request 参数也加入
        if 'request' in url_args:
            kw['request'] = request 
        
        # 检查参数表中有无参数缺失
        for key, arg in url_args.items():
            # request 不能为可变长参数
            # if key == 'request' and arg.kind in (arg.VAR_POSITIONAL, arg.VAR_KEYWORD):
            if key == 'request' and arg.kind in (inspect.Parameter.VAR_POSITIONAL, 
                inspect.Parameter.VAR_KEYWORD):
                return web.HTTPBadRequest(text='request parameter cannot be the var argument')
            # 如果参数类型不是变长列表或变长字典，可省略
            if arg.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                # 如果没有默认值，而且没有传值就报错
                if arg.default == arg.empty and arg.name not in kw:
                    return web.HTTPBadRequest(text='Miss argument: {}'.format(arg.name))
        logging.info('{} call with args: {}'.format(self._func.__name__, kw))
        try:
            return await self._func(**kw)
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)

# 添加一个模块的所有路由
def add_routes(app, module_name):
    try:
        mod = __import__(module_name, fromlist=['get_submodule'])
    except ImportError as e:
        raise e
    # 遍历mod的方法和属性，找处理方法
    # 由于我们定义的处理方法被 @get 或 @post 装饰，所以方法里会有 __method__ 和 __route__
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        func = getattr(mod, attr)
        if callable(func) and hasattr(func, '__method__') and hasattr(func, '__route__'):
            args = ', '.join(inspect.signature(func).parameters.keys())
            logging.info('add route {} {} => {}({})'.format(func.__method__, func.__route__, func.__name__, args))
            app.router.add_route(func.__method__, func.__route__, RequestHandler(func))

# 添加静态文件路径
def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logging.info('add static {} => {}'.format('/static/', path))

