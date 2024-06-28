import argparse
import textwrap
from enum import Enum

from .generate_types import run


def show_help():
    help = """
    Usage: python3 -m izaber_wamp_zerp [command]

    ZERP command line utilities.
    
    Commands:
      help             Display this help message.
      generate-types   Generate ZERP types on your local machine to provide type hints to the izaber_wamp_zerp library. 
                       Requires Python >= 3.8.
    """
    print(textwrap.dedent(help))


class Command(str, Enum):
    """Valid commands accepted by the `izaber_wamp_zerp` command line utility."""

    HELP = "help"
    GENERATE = "generate-types"
    IGNORE_ERRORS = "--ignore-errors"


def initialize_parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="izaber_wamp_zerp",
        description="izaber_wamp_zerp command line utilities."
    )
    subparsers = parser.add_subparsers(dest="command", help="Generate ZERP types on your local machine that provide type hints to the izaber_wamp_zerp library. Requires Python >= 3.8.")
    parser_generate_types = subparsers.add_parser(Command.GENERATE.value)
    parser_generate_types.add_argument(
        Command.IGNORE_ERRORS.value,
        action="store_true",
        help="suppress any errors that occur and continue generating"
    )
    return parser


def main():
    """Entry point for the `izaber_wamp_zerp` command line utility."""
    parser = initialize_parse()
    args = parser.parse_args()
    if args.command == Command.GENERATE:
        return run(args.ignore_errors)

    

if __name__ == "__main__":
    main()
