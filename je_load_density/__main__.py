import argparse
import json
import sys
from typing import List, Optional

from je_load_density.utils.exception.exception_tags import argparse_get_wrong_data
from je_load_density.utils.executor.action_executor import execute_action, execute_files
from je_load_density.utils.file_process.get_dir_file_list import get_dir_files_as_list
from je_load_density.utils.json.json_file.json_file import read_action_json
from je_load_density.utils.project.create_project_structure import create_project_dir
from je_load_density.utils.socket_server.load_density_socket_server import (
    start_load_density_socket_server,
)


def _cmd_run(args: argparse.Namespace) -> None:
    execute_action(read_action_json(args.file))


def _cmd_run_dir(args: argparse.Namespace) -> None:
    execute_files(get_dir_files_as_list(args.dir))


def _cmd_run_str(args: argparse.Namespace) -> None:
    payload = args.json
    if sys.platform in {"win32", "cygwin", "msys"}:
        first_pass = json.loads(payload)
        if isinstance(first_pass, str):
            payload = first_pass
        else:
            execute_action(first_pass)
            return
    execute_action(json.loads(payload))


def _cmd_init(args: argparse.Namespace) -> None:
    create_project_dir(args.path)


def _cmd_serve(args: argparse.Namespace) -> None:
    start_load_density_socket_server(
        host=args.host,
        port=args.port,
        framed=args.framed,
        token=args.token,
        certfile=args.tls_cert,
        keyfile=args.tls_key,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="je_load_density")
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="execute one action JSON file")
    run.add_argument("file", type=str)
    run.set_defaults(func=_cmd_run)

    run_dir = sub.add_parser("run-dir", help="execute every action JSON in a directory")
    run_dir.add_argument("dir", type=str)
    run_dir.set_defaults(func=_cmd_run_dir)

    run_str = sub.add_parser("run-str", help="execute an inline action JSON string")
    run_str.add_argument("json", type=str)
    run_str.set_defaults(func=_cmd_run_str)

    init = sub.add_parser("init", help="create a project skeleton at PATH")
    init.add_argument("path", type=str)
    init.set_defaults(func=_cmd_init)

    serve = sub.add_parser("serve", help="start the TCP control socket server")
    serve.add_argument("--host", default="localhost")
    serve.add_argument("--port", type=int, default=9940)
    serve.add_argument("--framed", action="store_true", help="use length-prefixed framing")
    serve.add_argument("--token", default=None, help="shared-secret token (env LOAD_DENSITY_SOCKET_TOKEN)")
    serve.add_argument("--tls-cert", default=None)
    serve.add_argument("--tls-key", default=None)
    serve.set_defaults(func=_cmd_serve)

    # Legacy single-flag form, retained for backwards compatibility.
    parser.add_argument("-e", "--execute_file", type=str, help=argparse.SUPPRESS)
    parser.add_argument("-d", "--execute_dir", type=str, help=argparse.SUPPRESS)
    parser.add_argument("-c", "--create_project", type=str, help=argparse.SUPPRESS)
    parser.add_argument("--execute_str", type=str, help=argparse.SUPPRESS)

    return parser


def _dispatch_legacy(args: argparse.Namespace) -> bool:
    legacy_map = {
        "execute_file": lambda value: execute_action(read_action_json(value)),
        "execute_dir": lambda value: execute_files(get_dir_files_as_list(value)),
        "execute_str": lambda value: _cmd_run_str(argparse.Namespace(json=value)),
        "create_project": create_project_dir,
    }
    matched = False
    for key, action in legacy_map.items():
        value = getattr(args, key, None)
        if value is not None:
            matched = True
            action(value)
    return matched


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "func", None) is not None:
        args.func(args)
        return 0

    if _dispatch_legacy(args):
        return 0

    print(argparse_get_wrong_data, file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(repr(error), file=sys.stderr)
        sys.exit(1)
