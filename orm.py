#!/usr/bin/env python3
#-*- coding: utf-8 -*-
__author__ = 'dcje'

'''
选择 MYSQL 作为网站的后台数据库
执行 SQL 语句进行操作，并将常用的 SELECT INSERT 等语句进行函数封装
在异步框架的基础上，采用 aiomysql 作为数据库的异步 IO 驱动
将数据库中表的操作，映射成一个类的操作，也就是数据库表的一行映射成一个对象(ORM)
整个 ORM 也是异步操作
预备知识: python协程和异步IO(yield from 的使用) SQL 操作数据库 元类 面向对象知识
# -*----    -------     -*-
    如何定义一个 User 类，这个类和数据库中的表 USER 构成映射关系，二者应该关联起来，user 可以操作表USER
    通过 Field 类将 User 类的属性映射到 USER 表的列中，其中每一列的字段又有自己的一些属性，
    包括数据类型、列名、主键和默认值
'''

import asyncio, logging;logging.basicConfig(filename="webapp.log",filemode="a",format="%(asctime)s-%(name)s-%(levelname)s-%(message)s",level=logging.INFO)
# pip install aiomysql
import aiomysql

# 打印 SQL 查询语句
def log(sql, args=()):
    logging.info('SQL: %s' % (sql))

# 创建一个全局的连接池，每个 HTTP 请求都从池中获得数据库连接
@asyncio.coroutine
def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    for k, v in kw.items():
        print('%s ==> %s' % (k, v))
    # 全局变量 __pool 用于存储整个连接池
    global __pool
    __pool = yield from aiomysql.create_pool(
        host = kw.get('host', 'localhost'),
        user = kw['user'],
        password = kw['password'],
        db = kw['db'],
        port = kw.get('port', 3306),
        charset = kw.get('charset', 'utf8'),
        autocommit = kw.get('autocommit', True),
        # 默认最大连接数为10
        maxsize = kw.get('maxsize', 10),
        minsize = kw.get('minsize', 1),
        # 接收一个 event_loop 实例
        loop = loop
    )

# 封装 SQL SELECT 语句为 select 函数
@asyncio.coroutine
def select(sql, args, size=None):
    log(sql, args)
    global __pool

    # yield from 将会调用一个子协程，并直接返回调用的结果
    # yield from 从连接池中返回一个连接
    with (yield from __pool) as conn:
        # DictCursor is a cursor which returns results as a dictionary
        cur = yield from  conn.cursor(aiomysql.DictCursor) 
        # execute SQL
        yield from cur.execute(sql.replace('?', '%s'), args or ())
        
        # 根据指定返回的 size，返回查询结果
        if size:
            rs = yield from cur.fetchmany(size)
        else:
            rs = yield from cur.fetchall()

        logging.info('rows return: %s' % (len(rs)))
        return rs

# 封装 INSERT UPDAE DELETE
# 语句操作参数一样，所以定义一个通用的执行函数
# 返回操作影响的行号

@asyncio.coroutine
def execute(sql, args):
    log(sql, args)
    #global __pool
    with (yield from __pool) as conn:
        try:
            # execute 类型的SQL操作返回结果只有行号，所以不需要用 DictCursor
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace('?', '%s'), args)
            affectedLine = cur.rowcount
            yield from cur.close()
        except BaseException as e:
            raise
        return affectedLine
    
# 根据输入的参数生成占位符列表
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)

# 定义 Field 类，负责保存(数据库)表的字段和字段类型
class Field(object):
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    # 当打印表时，输出表的信息：类名 字段类型和名字
    def __str__(self):
        return '<%s, %s: %s>' % (self.__class__.__name__, self.column_type, self.name)

# 定义不同类型的衍生 Field
# 表的不同列字段类型不一样
class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, column_type='varchar(100)'):
        super().__init__(name, column_type, primary_key, default)

class BooleanField(Field):
    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

class IntegerField(Field):
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

# 定义 Model 的元类
# 所有的元类都继承自 type 
# ModelMetaclass 元类定义了所有 Model 基类的子类实现操作
# ModelMetaclas 的工作主要是为一个数据库表映射成一个封装的类做准备
# 读取具体子类的映射信息
# 创造类的时候，排除对 Model 类的修改
# 在当前类中查找所有的类属性(attrs)，如果找到 Field 属性，就将其保存到 __mappings__ 的 dict，
# 同时从类属性中删除 Field(防止实例属性遮住类的同名属性)
# 完成这些就可以在 Model 中定义各种数据库的操作方法
class ModelMetaclass(type):
    # __new__ 控制 __init__ 的执行，所以在其执行之前
    # cls: 代表要 __init__ 的类，此参数在实例化时由 python 解释器自动提供
    # bases: 代表继承父类的集合
    # attrs: 类的方法集合
    def __new__(cls, name, bases, attrs):
        # 排除 Model
        if 'Model' == name:
            return type.__new__(cls, name, bases, attrs)
        
        # 获取 table 名词
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))

        # 获取 Field 和主键名
        mappings = dict()
        fields = []
        primaryKey = None
        for k,v in attrs.items():
            # Field 属性 
            if isinstance(v, Field):
                # 此处打印的 k 是一个属性，v 是这个属性在数据库中对应的 Field 列表属性
                logging.info('  found mapping: %s --> %s' % (k, v))
                mappings[k] = v

                # 找到了主键 
                if v.primary_key:
                    # 如果此时类实例已存在主键，说明主键重复
                    if primaryKey:
                        raise StandardError('Duplicate primary key for field: %s' % k)
                    # 否则将此列设为主键
                    primaryKey = k
                else:
                    fields.append(k)

        if not primaryKey:
            raise StandardError('Primary key is not found')

        # 从类属性中删除 Field 属性
        for k in mappings.keys():
            attrs.pop(k)

        # 保存除主键外的属性名为``(运算出字符串)列表形式
        escaped_fields = list(map(lambda f:'`%s`' % f, fields))

        # 保存属性和列的映射关系
        attrs['__mappings__'] = mappings
        # 保存表名
        attrs['__table__'] = tableName
        # 保存主键属性名
        attrs['__primary_key__'] = primaryKey
        # 保存除主键外的属性名
        attrs['__fields__'] = fields

        # 构造默认的 SELECT INSERT UPDATE DELETE 语句为
        # `` 反引号功能同 repr()
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, 
            create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set `%s` where `%s` = ?' % (tableName, ', '.join(map(lambda f:'`%s`=?' % (mappings.get(f).name or f),
            fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)

# 定义 ORM 所有映射的基类 Model
# Model 类的任意子类可以映射一个数据库表
# Model 类可以看作是对所有数据库表操作的基本定义映射

# 基于字典查询形式
# Model 从 dict 继承，拥有字典的所有功能，同时实现特殊方法 __getattr__ 和 __setattr__，实现属性操作
# 实现数据库操作的所有方法，定义为 class 方法，所有继承自 Model 都具有数据库操作方法
class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r'"Model" object has no attribute: %s' % (key))

    def __setattr__(self, key, value):
        self[key] = value
    
    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value

    @classmethod
    # 类方法有类变量 cls 传入，从而可以用 cls 做一些相关的处理，并且有子类继承时，调用该类方法，传入的变量 cls 是子类，而非父类
    @asyncio.coroutine
    def findAll(cls, where=None, args=None, **kw):
        '''find object by where clause'''
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)

        if args is None:
            args = []

        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)

        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = yield from select(' '.join(sql), args)
        return [cls(**r) for r in rs]

    @classmethod
    @asyncio.coroutine
    def findNumber(cls, selectField, where=None, args=None):
        '''find number by select and where'''
        sql = ['select %s __num__ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = yield from select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['__num__']

    @classmethod
    @asyncio.coroutine
    def find(cls, primaryKey):
        '''find object by primary key'''
        rs = yield from select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [primaryKey], 1)
        if 0 == len(rs):
            return None
        return cls(**rs[0])

    @asyncio.coroutine
    def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = yield from execute(self.__insert__, args)
        logging.info(args)
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' % rows)

    @asyncio.coroutine
    def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = yield from execute(self.__update__, args)
        if rows != 1:
            logging.warn('failed to update by primary key: affected rows: %s' % rows)

    @asyncio.coroutine
    def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = yield from execute(self.__delete__,args)
        if rows != 1:
            logging.warn('failed to remove by primary key: affected rows: %s' % rows)
