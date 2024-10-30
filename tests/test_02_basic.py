#!/usr/bin/env python3

from .utils import *

from izaber import initialize
from izaber.wamp.zerp import zerp

def test_connection():
    snapshot_data = load_nexus_db()
    users = snapshot_data['users']

    # Try to login manually
    username = 'backend-1'
    password = users[username]['plaintext_password']

    # Let's create a local version of the
    # izaber.yaml file
    izaber_fpath = TEST_PATH / 'izaber.yaml'
    izaber_fh = izaber_fpath.open('w')
    izaber_fh.write(
        IZABER_TEMPLATE.format(
            username=username,
            password=password
        )
    )
    izaber_fh.close()


    initialize('test', environment="live")

    zerp.hello(__file__, author="Aki", version="0.1a", description="testing errors in izaber-wamp-zerp")

    oo = zerp.get('product.product')
    assert oo

    search_results = oo.search([('active','=',True)],limit=1)
    assert len(search_results) == 1

    data = oo.read(search_results,['name','default_code'])
    assert data

if __name__ == '__main__':
    test_connection()
