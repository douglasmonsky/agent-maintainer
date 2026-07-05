"""Command line interface for the task broker incubator."""

from __future__ import annotations

import argparse
import sys
from importlib import metadata
from pathlib import Path

from agent_task_broker.store import BrokerError, BrokerStore


def console_main() -> int:
    """Run console entrypoint."""
    return main(sys.argv[1:])


def main(argv: list[str] | None = None) -> int:
    """Run task broker command."""
    parser = build_parser()
    args = parser.parse_args(argv)
    store = BrokerStore(root=args.root)
    try:
        return run_command(args, store)
    except BrokerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser."""
    parser = argparse.ArgumentParser(prog="agent-task-broker")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="initialize broker state")
    init_parser.add_argument("--force", action="store_true", help="replace board metadata")

    add_parser = subparsers.add_parser("add", help="add one task")
    add_parser.add_argument("title")
    add_parser.add_argument("--body", default="")
    add_parser.add_argument("--priority", type=int, default=0)

    list_parser = subparsers.add_parser("list", help="list tasks")
    list_parser.add_argument("--status")

    subparsers.add_parser("next", help="print next open task")

    claim_parser = subparsers.add_parser("claim", help="claim one task")
    claim_parser.add_argument("task_id")
    claim_parser.add_argument("--agent", required=True)

    complete_parser = subparsers.add_parser("complete", help="complete one task")
    complete_parser.add_argument("task_id")
    complete_parser.add_argument("--summary", required=True)

    give_up_parser = subparsers.add_parser("give-up", help="give up one task")
    give_up_parser.add_argument("task_id")
    give_up_parser.add_argument("--reason", required=True)

    return parser


def run_command(args: argparse.Namespace, store: BrokerStore) -> int:
    """Run parsed command."""
    match args.command:
        case "init":
            store.init(force=args.force)
            print(f"Initialized {store.board_dir}")
        case "add":
            task = store.add_task(args.title, body=args.body, priority=args.priority)
            print(format_task(task))
        case "list":
            print_tasks(store.tasks(status=args.status))
        case "next":
            print_next_task(store.next_task())
        case "claim":
            attempt = store.claim_task(args.task_id, agent=args.agent)
            print(f"CLAIMED {attempt['task_id']} attempt {attempt['id']}")
        case "complete":
            result = store.complete_task(args.task_id, summary=args.summary)
            print(f"COMPLETED {result['task_id']}: {result['summary']}")
        case "give-up":
            result = store.give_up_task(args.task_id, reason=args.reason)
            print(f"GAVE-UP {result['task_id']}: {result['summary']}")
        case _:
            raise BrokerError(f"unknown command: {args.command}")
    return 0


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
