#!/usr/bin/env python3

import sys

def test_import():
    print("\nWe are using python version:", sys.version)
    try:
        import izaber
        import izaber.wamp.zerp
    except Exception as ex:    
        pass

if __name__ == '__main__':
    test_import()
