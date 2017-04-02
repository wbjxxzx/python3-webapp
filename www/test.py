#!/usr/bin/env python3
import orm
from models import User
import asyncio, sys
from aiohttp import web

loop = asyncio.get_event_loop()

@asyncio.coroutine
def test():
    yield from orm.create_pool(loop=loop,user='dcje', password='123', 
        host='localhost',port=3306, db='py_web')
    u = User(name='admin', email='admin@admin.com', passwd='admin', image='about:blank')
    yield from u.save()

loop.run_until_complete(test())