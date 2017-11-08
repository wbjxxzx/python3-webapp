#!/usr/bin/env python3
#-*- coding:utf-8 -*-
__author__ = 'Ming'

import json, logging, inspect, functools

class APIError(Exception):
    ''' the base APIError which contains error(required), data(optional) and message(optional) '''
    def __init__(self, error, data='', message=''):
        super(APIError, self).__init__(message)
        self.error = error
        self.data  = data
        self.message = message

class APIValueError(APIError):
    pass

class APIPermissionError(APIError):
    pass

class Page(object):
    def __init__(self, item_count, page_index=1, page_size=10):
        self.item_count = item_count
        self.page_size = page_size
        self.page_count = item_count // page_size + (1 if item_count % page_size > 0 else 0)
        if (item_count == 0) or (page_index > self.page_count):
            self.offset = 0
            self.limit = 0
            self.page_index = 1
        else:
            self.page_index = page_index
            self.offset = self.page_size * (page_index - 1)
            self.limit = self.page_size
        self.has_next = self.page_index < self.page_count
        self.has_previous = self.page_index > 1

    def __str__(self):
        return 'item_count: {}, page_count: {}, page_index: {}, page_size: {}, offset: {}, limit: {}'.format(
            self.item_count, self.page_count, self.page_index, self.page_size, self.offset, self.limit
    )
