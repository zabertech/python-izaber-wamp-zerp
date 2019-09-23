"""
Usage:
    {name}
        [-e=<val> | --environment=<val>]
    {name} call <command>
        [-e=<val> | --environment=<val>]
    {name} pub <command>
        [-e=<val> | --environment=<val>]
    {name} sub <command>
        [-e=<val> | --environment=<val>]

Options:
    -e=<val>, --environment=<val>
                    The environment (defined in the ~/izaber.yaml) to use for
                    process. [default: ]
    
External Dependencies:
    - iZaber for communication to ZERP
        python3 -m pip install izaber-wamp-zerp
    - docopt for handling command line arguments
        python3 -m pip install docopt

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

import swampyer
from docopt import docopt

from izaber import initialize
from izaber.wamp.zerp import zerp
from izaber.wamp.zerp import wamp

from cmd import Cmd
import sys
import re
import os
import asyncio
import time

from pprint import pprint
from datetime import datetime

# REPL --------------------------------------------------------------------------------------------

class replPrompt(Cmd):
    reg_uri_list = {}
    sub_uri_list = {}

    # HELPERS ---------------------------------------------

    def parse_args(self, args):
        # Apply stdin if needed before doing anything else
        args = args.format(stdin=global_args['stdin'])

        # This regex looks for the (....) part of the args
        reResult = re.search(r'\(.*\)', args)
        if not reResult:
            raise Exception('No arguments provided. Use "help" for proper syntax')

        params = reResult.group()
        params = params.replace('(', '')
        params = params.replace(')', '') 
        uri = args[0:reResult.span()[0]]

        return uri, params

    def call_uri(self, uri, *args, **kwargs):
        uri_base_bkp = wamp.wamp.uri_base
        wamp.wamp.uri_base = ''

        try:
            if not (uri.startswith('com') or uri.startswith('wamp')):
                uri = f'{uri_base_bkp}.zerp:{zerp.database}:{uri}'
            return wamp.wamp.call(uri, *args, **kwargs)
        finally:
            # Reset the uri_base no matter what happens
            wamp.wamp.uri_base = uri_base_bkp

    def publish_uri(self, uri, *args, **kwargs):
        uri_base_bkp = wamp.wamp.uri_base
        wamp.wamp.uri_base = ''

        try:
            if not (uri.startswith('com') or uri.startswith('wamp')):
                uri = f'{uri_base_bkp}.zerp:{zerp.database}:{uri}'
            pub_metadata = wamp.wamp.publish(uri, *args, **kwargs)

            if not pub_metadata:
                raise Exception(f"publish call returned '{pub_metadata}")
            
            #if 'error' in pub_metadata[4]:
            #    print(pub_metadata)
            #    raise Exception(pub_metadata[5])
        finally:
            # Reset the uri_base no matter what happens
            wamp.wamp.uri_base = uri_base_bkp

    def subscribe_uri(self, uri, *args, **kwargs):
        uri_base_bkp = wamp.wamp.uri_base
        wamp.wamp.uri_base = ''

        try:
            if not (uri.startswith('com') or uri.startswith('wamp')):
                uri = f'{uri_base_bkp}.zerp:{zerp.database}:{uri}'

            sub_data = wamp.wamp.subscribe(uri, *args, **kwargs)

            if not sub_data:
                raise Exception(f"Could not subscribe to '{uri}'. Not allowed?")

            return sub_data
        finally:
            # Reset the uri_base no matter what happens
            wamp.wamp.uri_base = uri_base_bkp


    # CALLBACKS -------------------------------------------

    def sub_callback(_a, _b, *args, **kwargs):
        print(f'\n{datetime.now()} - Sub data received')
        pprint(args)
        pprint(kwargs)

    # REPL FUNCTIONS --------------------------------------

    def do_call(self, args):
        """
        - Call a uri with the given args and kwargs
        - The args and kwargs must be provided in the python format
        - syntax
   
            call <uri_to_call>(arg1, arg2, kwarg1=val1, ...)

        - example
   
            call com.ghar.api.randtext.generate('8pc', count=5)
        """

        try:
            uri, params = self.parse_args(args)
            result = eval(f'self.call_uri(\'{uri}\', {params})')
            pprint(result)
        except Exception as e:
            print(e)

    def do_pub(self, args):
        """
        - publish data to a uri with the given args and kwargs
        - The args and kwargs must be provided in the python format
            - args should be an array 
            - kwargs should be a dict
        - syntax
            
            pub <uri_to_call>(args=[arg1, arg2], kwargs={ kwarg1: val1 })

        - example
            
            pub com.ghar.api.some_sub(args=[1, 2], kwargs={ var1: 42 })
        """

        try:
            uri, params = self.parse_args(args)
            print(eval(f'self.publish_uri(\'{uri}\', {params})'))
        except Exception as e:
            print(e)

    def do_sub(self, args):
        """
        - subscribe to a URI and listen for any published events on the same URI
        - No arguments must be provided
        - You will not be able to interact with the shell any more because the
          CLI is waiting for data to be published to the URI
        - Published args and kwargs will be printed to the shell when a publish
          event occurs on the URI
        - To exit and stop the subscription use a keyboard interrup (Ctrl + C)
        - syntax
            
            sub <uri_to_subscribe_to>

        - example
            
            sub com.ghar.api.some_sub
        """

        # Apply stdin if needed before doing anything else
        args = args.format(stdin=global_args['stdin'])

        # Prepare a new async event loop that will wait for published results efficiently
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Data about the subscription that will be needed when we want to unsubscribe
        sub_metadata = None

        try:
            sub_metadata = self.subscribe_uri(args, self.sub_callback)
            print(sub_metadata)
            print(f'Listening for publish events on {args}')

            # Keep the process alive for ever (until a keyboard interrupt happens)
            loop.run_forever()
        except KeyboardInterrupt:
            # This is here to prevent it from propagating to the try except in 'main' which would
            # have closed the REPL completely
            pass
        except Exception as e:
            print(e)
        finally:
            # Stop the event loop and unsubscribe from the wamp subscription
            loop.stop()
            loop.close()
            if sub_metadata:
                print(f'Unsubscribing from {args}')
                wamp.wamp.unsubscribe(sub_metadata.subscription_id)

    def do_quit(self, args):
        """Quits the program."""

        print('Quitting')
        raise SystemExit

# MAIN --------------------------------------------------------------------------------------------

def run_main():
    global global_args

    global_args = docopt(__doc__.format(
        name=os.path.basename(__file__),
        stdin='{stdin}'
    ))

    # Parse stdin data if it exists and put it in args
    global_args['stdin'] = ''
    global_args['stdin_provided'] = not sys.stdin.isatty()
    if global_args['stdin_provided']:
        for line in sys.stdin:
            global_args['stdin'] += line
    global_args['stdin'] = global_args['stdin'].rstrip()

    # Connect to Zerp over the WAMP messagebus
    if global_args['--environment']:
        # Use the user defined environment
        print('Using env:', global_args['--environment'])
        initialize('izaber-wamp', environment=global_args['--environment'])
    else:
        # Use the default environment
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