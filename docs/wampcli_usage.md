# WAMP CLI

A CLI for making basic WAMP calls

## Commands

- call
    - Call a uri with the given args and kwargs
    - The args and kwargs must be provided in the python format
    - syntax
        
        ```
        call <uri_to_call>(arg1, arg2, kwarg1=val1, ...)
        ```
    - example
        
        ```
        call com.ghar.api.randtext.generate('8pc', count=5)
        ```
- pub
    - publish data to a uri with the given args and kwargs
    - The args and kwargs must be provided in the python format
        - args should be an array
        - kwargs should be a dict
    - syntax
        
        ```
        pub <uri_to_call>(args=[arg1, arg2], kwargs={ kwarg1: val1 })
        ```
    - example
        
        ```
        pub com.ghar.api.some_sub(args=[1, 2], kwargs={ var1: 42 })
        ```
- help
    - print the available commands in the REPL and how to use them
- quit
    - exit the REPL

# Using STDIN

- You can also pass in data through stdin by piping data into {name}.
- You can make use of stdin value by using '{stdin}' in your normal wampcli commands.
- Stdin can be any string and it will just be substitued into the command where '{stdin}' is defined.
- This means that the whole command could be obtained from stdin if needed as long as the command format remains valid after the substitution has taken place.
- For example: The following calls will effectively call "com.some.uri('Hello')". Be careful to put single quotes around '{stdin}' as shown when intending stdin to be used as a string

```
echo Hello | wampcli call "com.some.uri('{stdin}')"

echo "uri('Hello'" | wampcli call "com.some.{stdin})"

echo "uri('Hello'" > test
cat test | wampcli call "com.some.{stdin})"
```

**NOTE**: stdin will also work in the REPL. It will only work in
standalone calls on the command line
