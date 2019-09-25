"""
Usage:
    wampcli
        [-e=<val> | --environment=<val>]
        [-d | --debug]
        [-l | --all-logs]
    wampcli call <command>
        [-e=<val> | --environment=<val>]
        [-d | --debug]
        [-l | --all-logs]
    wampcli pub <command>
        [-e=<val> | --environment=<val>]
        [-d | --debug]
        [-l | --all-logs]
    wampcli sub <command>
        [-e=<val> | --environment=<val>]
        [-d | --debug]
        [-l | --all-logs]

Options:
    -e=<val>, --environment=<val>
                    The environment (defined in the ~/izaber.yaml) to use for
                    process. Useful for changing the nexus server or the 
                    databases used for the wamp calls [default: ]
    -d, --debug     Print out debug information for the wamp operations.
                    Helpful for understanding why a call might be failing
    -l, --all-logs
                    Log everything about the wamp communication down to the
                    packets being exchanged. It essentially sets the log level
                    to 1 (i.e. logs everything) and prints the logs to stdout

Config File:
    In order to communicate with Zerp, copy the following 
    into a file named ~/izaber.yaml and replace the username 
    and password with your zerp username and password. These
    settings will run the script in the sandbox.

        default:
            wamp:
                connection:
                    url: 'wss://nexus.izaber.com/ws'
                    username: 'zaber'
                    password: 'low_security_password'
                zerp:
                    database: 'sandbox'
    
    Based on your OS, place this file in
        Linux: /home/<yourusername>/izaber.yaml
        MacOS: /Users/<yourusername>/izaber.yaml
        Windows: \\Users\\<yourusername>\\izaber.yaml
"""

from __future__ import print_function
from __future__ import absolute_import

import swampyer
from docopt import docopt

from izaber import initialize
from . import zerp
from . import wamp
from .controller import METHOD_SHORTHANDS

from cmd import Cmd
import sys
import re
import os
import time

from pprint import pprint
from datetime import datetime
import traceback
import logging

# REPL --------------------------------------------------------------------------------------------

class replPrompt(Cmd):
    reg_uri_list = {}
    sub_uri_list = {}

    # HELPERS ---------------------------------------------

    def parse_args(self, args):
        # Apply stdin if needed before doing anything else. Not using args.format() because it
        # gets tripped up over other user provided usage of curly {} brackets
        args = args.replace('{stdin}', global_args['stdin'])

        # This regex looks for the (....) part of the args
        reResult = re.search(r'\(.*\)', args)
        if not reResult:
            raise Exception('No arguments provided. Use "help" for proper syntax')

        # Get the captured group but remove the 1 and last character (the brackets)
        uri = args[0:reResult.start()]
        params = reResult.group()[1:-1]

        return uri, params

    def get_expanded_shorthand_uri(self, uri_base, raw_uri):
        reResult = re.search(r'\.\..*$', raw_uri)
        if reResult:
            shorthand = reResult.group()[2:]
            model = raw_uri[0:reResult.start()]

            shorthand_method = METHOD_SHORTHANDS.get(shorthand, '')
            if not shorthand_method:
                # The shorthand has no existing method defined for it so we can try and assume that
                # the shorthand_method should have the format `object.execute.<shorthand>`
                shorthand_method = 'object.execute.{}'.format(shorthand)

            return '{}.zerp:{}:{}:{}'.format(
                uri_base,
                zerp.database,
                model,
                shorthand_method
            )
        else:
            raise Exception("Could not parse the shorthand URI: {}".format(raw_uri))

    def get_full_zerp_uri(self, uri_base, raw_uri):
        # Return the raw_uri as is if it starts with `com` or `wamp` because we can assume the
        # user provided us with the full URI in these cases
        if raw_uri.startswith('com') or raw_uri.startswith('wamp'):
            return raw_uri

        # If there is a `..` in the raw_uri then we can assume that the user provided us with a
        # shorthand version of the full URI. For example
        #   A shorthand like this: product.product..read()
        #   needs to become a URI like this: com.izaber.wamp.zerp:<db_name>:product.product:object.execute.read()
        if '..' in raw_uri:
            return self.get_expanded_shorthand_uri(uri_base, raw_uri)

        # If the raw_uri did not start with `com` or `wamp`, and did not use the shorthand notation
        # then we can assume that the user provided us with the ending part of the URI i.e. the part
        # the database name. For example:
        #   A raw_uri like this: product.product:object.execute.read()
        #   needs to become a URI like this: com.izaber.wamp.zerp:<db_name>:product.product:object.execute.read()
        return '{}.zerp:{}:{}'.format(
            uri_base, 
            zerp.database, 
            raw_uri
        )

    def call_uri(self, uri, *args, **kwargs):
        uri_base_bkp = wamp.wamp.uri_base
        wamp.wamp.uri_base = ''

        try:
            full_uri = self.get_full_zerp_uri(uri_base_bkp, uri)

            if global_args['--debug']:
                print('operation: call')
                print('input URI:', uri)
                print('full URI used:', full_uri)
                print('args:', args)
                print('kwargs:', kwargs)

            result = wamp.wamp.call(full_uri, *args, **kwargs)

            if global_args['--debug']:
                print('result:', result)

            return result
        finally:
            # Reset the uri_base no matter what happens
            wamp.wamp.uri_base = uri_base_bkp

    def publish_uri(self, uri, *args, **kwargs):
        uri_base_bkp = wamp.wamp.uri_base
        wamp.wamp.uri_base = ''

        try:
            full_uri = self.get_full_zerp_uri(uri_base_bkp, uri)

            if global_args['--debug']:
                print('operation: publish')
                print('input URI:', uri)
                print('full URI used:', full_uri)
                print('args:', args)
                print('kwargs:', kwargs)

            pub_metadata = wamp.wamp.publish(full_uri, *args, **kwargs)

            if not pub_metadata or 'error' in str(pub_metadata):
                raise Exception("publish call returned: {}".format(pub_metadata))

            if global_args['--debug']:
                print('publish metadata:', pub_metadata)
        finally:
            # Reset the uri_base no matter what happens
            wamp.wamp.uri_base = uri_base_bkp

    def subscribe_uri(self, uri, *args, **kwargs):
        uri_base_bkp = wamp.wamp.uri_base
        wamp.wamp.uri_base = ''

        try:
            full_uri = self.get_full_zerp_uri(uri_base_bkp, uri)

            if global_args['--debug']:
                print('operation: subscribe')
                print('input URI:', uri)
                print('full URI used:', full_uri)
                print('args:', args)
                print('kwargs:', kwargs)

            sub_metadata = wamp.wamp.subscribe(full_uri, *args, **kwargs)

            if not sub_metadata or 'error' in str(sub_metadata):
                raise Exception("subscription call returned: {}".format(sub_metadata))

            if global_args['--debug']:
                print('subscription metadata:', sub_metadata)

            return sub_metadata
        finally:
            # Reset the uri_base no matter what happens
            wamp.wamp.uri_base = uri_base_bkp


    # CALLBACKS -------------------------------------------

    def sub_callback(_a, _b, *args, **kwargs):
        print('\n{} - Sub data received'.format(datetime.now()))
        pprint(args)
        pprint(kwargs)

    # REPL FUNCTIONS --------------------------------------

    def do_call(self, args):
        """
        - Call a uri with the given args and kwargs
        - The URI can be provided in 3 ways
            - Shorthand URIs for ZERP
                - A wamp URI like this: product.product..read
                - Becomes: com.izaber.wamp.zerp:<db_name>:product.product:object.execute.read
            - Short URIs for ZERP
                - A wamp URI like this: product.product:object.execute.read
                - Becomes: com.izaber.wamp.zerp:<db_name>:product.product:object.execute.read
            - The full URI starting with `com` or `wamp`. If the URI does not 
              start with `com` or `wamp` then the URI is assumed to be a 
              shortended URI
        - The args and kwargs must be provided in the python format
        - syntax
   
            call <uri_to_call>(arg1, arg2, kwarg1=val1, ...)

        - example: All of the following commands do that same thing
   
            call com.izaber.wamp.zerp:sandbox:product.product:object.execute.read(1596, ['default_code'])
            call product.product:object.execute.read(1596, ['default_code'])
            call product.product..read(1596, ['default_code'])
        """

        try:
            uri, params = self.parse_args(args)
            result = eval("self.call_uri(\'{}\', {})".format(uri, params))
            pprint(result)
        except Exception as e:
            if global_args['--debug']:
                traceback.print_exc()
            else:
                print('Error:', e)

    def do_pub(self, args):
        """
        - publish data to a uri with the given args and kwargs
        - The URI can be provided in 3 ways
            - Short URIs for ZERP
                - A wamp URI like this: product.product:object.execute.read
                - Becomes: com.izaber.wamp.zerp:<db_name>:product.product:object.execute.read
            - The full URI starting with `com` or `wamp`. If the URI does not 
              start with `com` or `wamp` then the URI is assumed to be a 
              shortended URI
        - The args and kwargs must be provided in the python format
            - args should be an array 
            - kwargs should be a dict
        - syntax
            
            pub <uri_to_call>(args=[arg1, arg2], kwargs={ kwarg1: val1 })

        - example
            
            pub com.izaber.wamp.wampcli.test(args=[1, 2], kwargs={ var1: 42 })
        """

        try:
            uri, params = self.parse_args(args)
            eval("self.publish_uri(\'{}\', {})".format(uri, params))
        except Exception as e:
            if global_args['--debug']:
                traceback.print_exc()
            else:
                print('Error:', e)

    def do_sub(self, args):
        """
        - subscribe to a URI and listen for any published events on the same URI
        - The URI can be provided in 3 ways
            - Short URIs for ZERP
                - A wamp URI like this: product.product:object.execute.read
                - Becomes: com.izaber.wamp.zerp:<db_name>:product.product:object.execute.read
            - The full URI starting with `com` or `wamp`. If the URI does not 
              start with `com` or `wamp` then the URI is assumed to be a 
              shortended URI
        - No arguments must be provided
        - You will not be able to interact with the shell any more because the
          CLI is waiting for data to be published to the URI
        - Published args and kwargs will be printed to the shell when a publish
          event occurs on the URI
        - To exit and stop the subscription use a keyboard interrup (Ctrl + C)
        - syntax
            
            sub <uri_to_subscribe_to>

        - example
            
            sub com.izaber.wamp.wampcli.test
        """

        # Apply stdin if needed before doing anything else
        args = args.format(stdin=global_args['stdin'])

        # Data about the subscription that will be needed when we want to unsubscribe
        sub_metadata = None

        try:
            sub_metadata = self.subscribe_uri(args, self.sub_callback)
            print('Listening for publish events on {}'.format(args))

            # Keep the process alive for ever (until a keyboard interrupt happens)
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            # This is here to prevent it from propagating to the try except in 'main' which would
            # have closed the REPL completely
            pass
        except Exception as e:
            if global_args['--debug']:
                traceback.print_exc()
            else:
                print('Error:', e)
        finally:
            # Stop the wait loop and unsubscribe from the wamp subscription
            if sub_metadata:
                print('Unsubscribing from {}'.format(args))
                wamp.wamp.unsubscribe(sub_metadata.subscription_id)

    def do_EOF(self, line):
        return True

    def do_quit(self, args):
        """Quits the program."""

        print('\nQuitting')
        raise SystemExit

# MAIN --------------------------------------------------------------------------------------------

def run_main():
    global global_args

    global_args = docopt(__doc__)

    # Parse stdin data if it exists and put it in args
    global_args['stdin'] = ''
    global_args['stdin_provided'] = not sys.stdin.isatty()
    if global_args['stdin_provided']:
        for line in sys.stdin:
            global_args['stdin'] += line
    global_args['stdin'] = global_args['stdin'].rstrip()

    # Enable full logging if user wants
    if global_args['--all-logs']:
        logging.basicConfig(stream=sys.stdout, level=1)

    # Connect to Zerp over the WAMP messagebus
    if global_args['--environment']:
        # Use the user defined environment
        if global_args['--debug']:
            print('Using env:', global_args['--environment'])
        initialize('izaber-wamp', environment=global_args['--environment'])
    else:
        # Use the default environment
        if global_args['--debug']:
            print('Using env: default')
        initialize('izaber-wamp')

    # Initialize the REPL
    repl = replPrompt()

    if global_args['call']:
        repl.do_call(''.join(global_args['<command>']))
        exit()

    if global_args['pub']:
        repl.do_pub(''.join(global_args['<command>']))
        exit()

    if global_args['sub']:
        repl.do_sub(''.join(global_args['<command>']))
        exit()

    # The cmdloop REPL freaks out for some reason when there is data provided in stdin
    # So we do not want to allow that
    if global_args['stdin_provided']:
        print('Cannot run REPL when stdin is provided')
        exit()

    try:
        # If there were no extra commands provided and there is no stdin then start the REPL
        repl.prompt = '> '
        repl.cmdloop('Starting WAMP CLI')
    except KeyboardInterrupt:
        print('Quitting')
        raise SystemExit

if __name__ == '__main__':
    run_main()