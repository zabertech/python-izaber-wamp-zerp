#!/usr/bin/env python3

def test_import():
    try:
        import izaber
        import izaber.wamp.zerp
    except Exception as ex:    
        pass

if __name__ == '__main__':
    test_import()
