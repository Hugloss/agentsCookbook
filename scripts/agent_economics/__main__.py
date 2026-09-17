from __future__ import annotations

import sys

from .context_focus_cli import main as context_focus_main


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "context-focus":
        context_focus_main(args[1:])
        return

    # Preserve the pre-P6 package behavior: arguments without a subcommand are
    # routed to refactor-focus. Import lazily so context-focus remains usable
    # when copied with only its own portable dependencies.
    from .refactor_focus_cli import main as refactor_focus_main

    if args and args[0] == "refactor-focus":
        args = args[1:]
    refactor_focus_main(args)


if __name__ == "__main__":
    main()
