from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "context-focus":
        from .context_focus_cli import main as context_focus_main

        context_focus_main(args[1:])
        return
    if args and args[0] == "test-focus":
        from .test_focus_cli import main as test_focus_main

        test_focus_main(args[1:])
        return
    if args and args[0] == "change-impact":
        from .change_impact_cli import main as change_impact_main

        change_impact_main(args[1:])
        return
    if args and args[0] == "coupling-focus":
        from .coupling_focus_cli import main as coupling_focus_main

        coupling_focus_main(args[1:])
        return
    if args and args[0] == "hotspot-focus":
        from .hotspot_focus_cli import main as hotspot_focus_main

        hotspot_focus_main(args[1:])
        return

    if args and args[0] == "quality-debt":
        from .quality_debt_cli import main as quality_debt_main

        quality_debt_main(args[1:])
        return
    if args and args[0] == "capabilities":
        from .capabilities import main as capabilities_main

        capabilities_main(args[1:])
        return
    if args and args[0] == "run-command":
        from .command_runner import main as command_runner_main

        command_runner_main(args[1:])
        return
    if args and args[0] == "qualify-local":
        from .local_qualify import main as local_qualify_main

        local_qualify_main(args[1:])
        return
    if args and args[0] == "benchmark-outcomes":
        from .agent_outcome_benchmark import main as benchmark_main

        benchmark_main(args[1:])
        return

    from .refactor_focus_cli import main as refactor_focus_main

    if args and args[0] == "refactor-focus":
        args = args[1:]
    refactor_focus_main(args)


if __name__ == "__main__":
    main()
