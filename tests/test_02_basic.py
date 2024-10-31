#!/usr/bin/env python3

from .utils import *

from izaber import initialize
from izaber.wamp.zerp import zerp

def test_connection():
    initialize()

    zerp.hello(__file__, author="Aki", version="0.1a", description="testing errors in izaber-wamp-zerp")

    oo = zerp.get('product.product')
    assert oo

    search_results = oo.search([('active','=',True)],limit=1)
    assert len(search_results) == 1

    data = oo.read(search_results,['name','default_code'])
    assert data

if __name__ == '__main__':
    test_connection()
