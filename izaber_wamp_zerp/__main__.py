import sys
import textwrap
from enum import Enum

from .generate_types import run


def show_help():
    help = """
    Usage: python3 -m izaber_wamp_zerp [command]

    ZERP command line utilities.
    
    Commands:
      help             Display this help message.
      generate-types   Generate ZERP types on your local machine that provide type hints to the izaber_wamp_zerp library. 
                       Requires Python >= 3.8.
    """
    print(textwrap.dedent(help))


class Command(str, Enum):
    """Valid commands accepted by the `izaber_wamp_zerp` command line utility."""

    HELP = "help"
    GENERATE = "generate-types"


def main():
    """Entry point for the `izaber_wamp_zerp` command line utility."""
    if not len(sys.argv) > 1:
        return show_help()
    elif sys.argv[1] == Command.HELP:
        return show_help()
    elif sys.argv[1] == Command.GENERATE:
        return run()
    else:
        return show_help()
    

if __name__ == "__main__":
    main()
