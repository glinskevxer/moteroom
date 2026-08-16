"""Running the package as a module.

`moteroom` is installed as a command, and on a machine where that has not
happened yet `python -m moteroom` has to do the same thing. It is the same
command tree either way, and this is the difference between somebody being
able to use a checkout and having to work out what to import.

Our own errors are turned into a line and a status here rather than a
traceback. A scale house operator does not want a stack, they want to know
which field the ticket was refused on.
"""

from __future__ import annotations

import sys

import click

from moteroom.cli.main import main
from moteroom.core.errors import MoteroomError

REFUSED = 1


def run(argv: list[str] | None = None) -> int:
    """Run the command tree and turn our own errors into a message."""
    try:
        main.main(args=argv if argv is not None else sys.argv[1:], standalone_mode=False)
    except MoteroomError as exc:
        click.echo(f"error: {exc}", err=True)
        return REFUSED
    except click.ClickException as exc:
        exc.show()
        return exc.exit_code
    except click.Abort:
        click.echo("aborted", err=True)
        return REFUSED
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
