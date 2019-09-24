# WAMP CLI

A command line program for making basic WAMP calls.

`wampcli` is automatically installed on your computer when you pip install the `izaber-wamp-zerp` module. Just open up `cmd` or a terminal and run `wampcli` to start using it.

It can be run in 2 modes
- REPL mode
    - Run it by calling `wampcli` in your command line
    - This open a custom command line where you can run ZERP related commands
    - The available commands are described in the [Commands](#commands) section below
- Standalone mode
    - All of the commands available in the REPL mode can also be run straight from the the command line itself.
    - This allows you to make use of stdin and stdout functionality in terminals
        - stdin usage is described in the [Using STDIN](#using-stdin) section
        - All output from the script can be easily routed to a file or other sink using the `>` operator in terminals
        - One can theoreticall
    - It also allows for one off calls that can be easily run from bash scripts, cron jobs, etc

## Options

The following options can be provided to `wampcli`

```
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
```

## Commands

- `call`
    - Call a uri with the given args and kwargs
    - The URI can be provided in 3 ways
        - Shorthand URIs for WAMP
            - A wamp URI like this: `product.product..read`
            - Becomes: `com.izaber.wamp.zerp:<db_name>:product.product:object.execute.read`
        - Short URIs for WAMP
            - A wamp URI like this: `product.product:object.execute.read`
            - Becomes: `com.izaber.wamp.zerp:<db_name>:product.product:object.execute.read`
        - The full URI starting with `com` or `wamp`. If the URI does not 
          start with `com` or `wamp` then the URI is assumed to be a 
          shortended URI
    - The args and kwargs must be provided in the python format
    - syntax

        ```
        call <uri_to_call>(arg1, arg2, kwarg1=val1, ...)
        ```
    - example: All of the following commands do that same thing

        ```
        call com.izaber.wamp.zerp:sandbox:product.product:object.execute.read(1596, ['default_code'])
        call product.product:object.execute.read(1596, ['default_code'])
        call product.product..read(1596, ['default_code'])
        ```
- `pub`
    - publish data to a uri with the given args and kwargs
    - The URI can be provided in 3 ways
        - Short URIs for WAMP
            - A wamp URI like this: `product.product:object.execute.read`
            - Becomes: `com.izaber.wamp.zerp:<db_name>:product.product:object.execute.read`
        - The full URI starting with `com` or `wamp`. If the URI does not 
          start with `com` or `wamp` then the URI is assumed to be a 
          shortended URI
    - The args and kwargs must be provided in the python format
        - args should be an array 
        - kwargs should be a dict
    - syntax

        ```
        pub <uri_to_call>(args=[arg1, arg2], kwargs={ kwarg1: val1 })
        ```
    - example

        ```
        pub com.izaber.wamp.wampcli.test(args=[1, 2], kwargs={ var1: 42 })
        ```
- `sub`
    - subscribe to a URI and listen for any published events on the same URI
    - The URI can be provided in 3 ways
        - Short URIs for WAMP
            - A wamp URI like this: `product.product:object.execute.read`
            - Becomes: `com.izaber.wamp.zerp:<db_name>:product.product:object.execute.read`
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
        
        ```
        sub <uri_to_subscribe_to>
        ```
    - example
        
        ```
        sub com.izaber.wamp.wampcli.test
        ```
- `help`
    - print the available commands in the REPL and how to use them
- `quit`
    - exit the REPL

## Using STDIN

- You can also pass in data through stdin by piping data into a standalone wampcli command.
    - Just add '{stdin}' in your normal wampcli commands where you want the stdin text to be substituted into the command.
    - Stdin can be any string and it will just be substitued into the command wherever '{stdin}' is defined.
    - This means that the whole command could be passed in through stdin if needed as long as the command format remains valid after the substitution has taken place.
- For example: The following calls will effectively call `com.some.uri('Hello')`

    ```
    echo Hello | wampcli call "com.some.uri('{stdin}')"

    echo "uri('Hello'" | wampcli call "com.some.{stdin})"

    echo "uri('Hello'" > test
    cat test | wampcli call "com.some.{stdin})"
    ```

**NOTE**: stdin will NOT work in the REPL. It will only work in standalone calls from the command line

## Chaining wampcli commands

Using the stdin functionality of `wampcli` you can pipe stdout from one command to the stdin of another `wampcli` command.

THe following example returns the `default_code` field of all products that have `X-LSQ` in their `default_code`

```
wampcli call "product.product..search([('default_code', 'like', 'X-LSQ')]) > ./search_ids.txt
cat ./search_ids.txt | wampcli call "product.product..read({stdin}, ['default_code'])
```

This can be turned directly into a one liner without having to create the intermediate `./search_ids.txt` file like this

```
wampcli call "product.product..search([('default_code', 'like', 'X-LSQ')]) | wampcli call "product.product..read({stdin}, ['default_code'])
```