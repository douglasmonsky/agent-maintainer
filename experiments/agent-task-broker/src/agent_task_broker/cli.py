"""Command line interface for the task broker incubator."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from importlib import metadata
from pathlib import Path

from agent_task_broker.handoff import render_handoff
from agent_task_broker.results import RESULT_STATUSES, ResultError, ResultInput
from agent_task_broker.results import result_payload as make_result_payload
from agent_task_broker.store import BrokerError, BrokerStore, TaskInput

CommandHandler = Callable[[argparse.Namespace, BrokerStore], None]


def console_main() -> int:
    """Run console entrypoint."""
    return main(sys.argv[1:])


def main(argv: list[str] | None = None) -> int:
    """Run task broker command."""
    parser = build_parser()
    args = parser.parse_args(argv)
    store = BrokerStore(root=args.root)
    try:
        run_command(args, store)
    except (BrokerError, ResultError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser."""
    parser = argparse.ArgumentParser(prog="agent-task-broker")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_init_parser(subparsers)
    add_add_parser(subparsers)
    add_list_parser(subparsers)
    subparsers.add_parser("next", help="print next open task")
    add_handoff_parser(subparsers)
    add_claim_parser(subparsers)
    add_complete_parser(subparsers)
    add_give_up_parser(subparsers)
    add_result_parser(subparsers)
    return parser


def add_init_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add init parser."""
    init_parser = subparsers.add_parser("init", help="initialize broker state")
    init_parser.add_argument("--force", action="store_true", help="replace board metadata")


def add_add_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add task parser."""
    add_parser = subparsers.add_parser("add", help="add one task")
    add_parser.add_argument("title")
    add_parser.add_argument("--body", default="")
    add_parser.add_argument("--priority", type=int, default=0)
    add_parser.add_argument("--allowed-path", action="append", default=[])
    add_parser.add_argument("--do-not-edit-path", action="append", default=[])
    add_parser.add_argument("--constraint", action="append", default=[])
    add_parser.add_argument("--evidence", action="append", default=[])
    add_parser.add_argument("--acceptance-command", action="append", default=[])


def add_list_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add list parser."""
    list_parser = subparsers.add_parser("list", help="list tasks")
    list_parser.add_argument("--status")


def add_handoff_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add handoff parser."""
    handoff_parser = subparsers.add_parser("handoff", help="render handoff capsule")
    handoff_parser.add_argument("task_id")
    handoff_parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
    )


def add_claim_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add claim parser."""
    claim_parser = subparsers.add_parser("claim", help="claim one task")
    claim_parser.add_argument("task_id")
    claim_parser.add_argument("--agent", required=True)


def add_complete_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add complete parser."""
    complete_parser = subparsers.add_parser("complete", help="complete one task")
    complete_parser.add_argument("task_id")
    complete_parser.add_argument("--summary", required=True)
    complete_parser.add_argument("--verification", action="append", default=[])
    complete_parser.add_argument("--changed-file", action="append", default=[])


def add_give_up_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add give-up parser."""
    give_up_parser = subparsers.add_parser("give-up", help="give up one task")
    give_up_parser.add_argument("task_id")
    give_up_parser.add_argument("--reason", required=True)


def add_result_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add structured result parser."""
    result_parser = subparsers.add_parser("result", help="write structured result")
    result_parser.add_argument("task_id")
    result_parser.add_argument("--status", choices=RESULT_STATUSES, required=True)
    result_parser.add_argument("--summary", default="")
    result_parser.add_argument("--verification", action="append", default=[])
    result_parser.add_argument("--needs", action="append", default=[])
    result_parser.add_argument("--reason", default="")
    result_parser.add_argument("--changed-file", action="append", default=[])


def run_command(args: argparse.Namespace, store: BrokerStore) -> None:
    """Run parsed command."""
    handlers: dict[str, CommandHandler] = {
        "init": handle_init,
        "add": handle_add,
        "list": handle_list,
        "next": handle_next,
        "handoff": handle_handoff,
        "claim": handle_claim,
        "complete": handle_complete,
        "give-up": handle_give_up,
        "result": handle_result,
    }
    handlers[args.command](args, store)


def handle_init(args: argparse.Namespace, store: BrokerStore) -> None:
    """Handle init command."""
    store.init(force=args.force)
    print(f"Initialized {store.board_dir}")


def handle_add(args: argparse.Namespace, store: BrokerStore) -> None:
    """Handle add command."""
    task = store.add_task(task_input_from_args(args))
    print(format_task(task))


def handle_list(args: argparse.Namespace, store: BrokerStore) -> None:
    """Handle list command."""
    print_tasks(store.tasks(status=args.status))


def handle_next(_args: argparse.Namespace, store: BrokerStore) -> None:
    """Handle next command."""
    print_next_task(store.next_task())


def handle_handoff(args: argparse.Namespace, store: BrokerStore) -> None:
    """Handle handoff command."""
    print(render_handoff(store.require_task(args.task_id), output_format=args.format))


def handle_claim(args: argparse.Namespace, store: BrokerStore) -> None:
    """Handle claim command."""
    attempt = store.claim_task(args.task_id, agent=args.agent)
    print(f"CLAIMED {attempt['task_id']} attempt {attempt['id']}")


def handle_complete(args: argparse.Namespace, store: BrokerStore) -> None:
    """Handle complete command."""
    result = store.complete_task(
        args.task_id,
        summary=args.summary,
        verification=args.verification,
        changed_files=args.changed_file,
    )
    print(f"COMPLETED {result['task_id']}: {result['summary']}")


def handle_give_up(args: argparse.Namespace, store: BrokerStore) -> None:
    """Handle give-up command."""
    result = store.give_up_task(args.task_id, reason=args.reason)
    print(f"ABANDONED {result['task_id']}: {result['summary']}")


def handle_result(args: argparse.Namespace, store: BrokerStore) -> None:
    """Handle structured result command."""
    result = store.result_task(make_result_payload(result_input_from_args(args, store)))
    print(f"RESULT {result['task_id']} {result['status']}")


def task_input_from_args(args: argparse.Namespace) -> TaskInput:
    """Return task input from parsed args."""
    return TaskInput(
        title=args.title,
        body=args.body,
        priority=args.priority,
        allowed_paths=tuple(args.allowed_path),
        do_not_edit_paths=tuple(args.do_not_edit_path),
        constraints=tuple(args.constraint),
        evidence=tuple(args.evidence),
        acceptance_commands=tuple(args.acceptance_command),
    )


def result_input_from_args(args: argparse.Namespace, store: BrokerStore) -> ResultInput:
    """Return result input from parsed args."""
    return ResultInput(
        root=store.root,
        task_id=args.task_id,
        status=args.status,
        summary=args.summary,
        verification=tuple(args.verification),
        needs=tuple(args.needs),
        reason=args.reason,
        changed_files=tuple(args.changed_file),
    )


def print_tasks(tasks: list[dict[str, object]]) -> None:
    """Print compact task list."""
    if not tasks:
        print("No tasks.")
        return
    for task in tasks:
        print(format_task(task))


def print_next_task(task: dict[str, object] | None) -> None:
    """Print next task."""
    if task is None:
        print("No open tasks.")
        return
    print(format_task(task))


def format_task(task: dict[str, object]) -> str:
    """Return one-line task summary."""
    return f"{task['id']} [{task['status']}] p{task.get('priority', 0)} {task['title']}"


def installed_agent_maintainer_version() -> str:
    """Return installed Agent Maintainer distribution version."""
    return metadata.version("agent-maintainer")


if __name__ == "__main__":
    raise SystemExit(console_main())
