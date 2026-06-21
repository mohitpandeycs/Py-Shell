import os
import readline
import subprocess
import sys
from functools import cache

from typing import Callable, Dict, List, Optional, Tuple


def _exit(*args: str) -> int:
    return -1


def _echo(*args: str) -> int:
    print(*args)
    return 0


def _type(*args) -> int:
    if len(args) == 0:
        return 1
    cmd = args[0]
    fn = _get_exec(cmd)
    if fn is not None:
        print(f"{cmd} is a shell builtin")
        return 0
    path: Optional[str] = _get_external_cmd(cmd)
    if path is not None:
        print(f"{cmd} is {path}")
        return 0

    print(f"{cmd}: not found", file=sys.stderr)
    return 1


def _pwd(*args: str) -> int:
    print(os.getcwd())
    return 0


@cache
def home() -> str:
    return os.environ.get("HOME")


def _cd(*args) -> int:
    if len(args) == 0:
        os.chdir(home())
        return 0
    d = args[0]
    if d == "~":
        os.chdir(home())
        return 0

    try:
        os.chdir(d)
        return 0
    except:
        print(f"cd: {d}: No such file or directory", file=sys.stderr)
        return 1


LAST_HISTORY_APPEND_INDEX = 0


def _history(*args) -> int:
    global LAST_HISTORY_APPEND_INDEX
    history_items = [
        f"    {i + 1}  {readline.get_history_item(i + 1)}"
        for i in range(readline.get_current_history_length())
    ]
    if len(args) < 2:
        n = int(args[0]) if len(args) == 1 else 0
        history_items = history_items[-n:]
        print("\n".join(history_items))
    if len(args) == 2:
        if args[0] == "-r":
            with open(args[1], "r") as f:
                more_items = [line.strip() for line in f.readlines()]
            for item in more_items:
                if not item:
                    continue
                readline.add_history(item)
        if args[0] == "-w":
            readline.write_history_file(args[1])
        if args[0] == "-a":
            readline.append_history_file(
                len(history_items) - LAST_HISTORY_APPEND_INDEX, args[1]
            )
            LAST_HISTORY_APPEND_INDEX = len(history_items)

    return 0


class Args:
    def __init__(
        self,
        cmd,
        args,
        stdout_redirection,
        stderr_redirection,
        stdout_append,
        stderr_append,
    ):
        self.cmd = cmd
        self.args = args
        self.stdout_redirection = stdout_redirection
        self.stderr_redirection = stderr_redirection
        self.stdout_append = stdout_append
        self.stderr_append = stderr_append

    def __repr__(self):
        return str(
            {
                "cmd": self.cmd,
                "args": self.args,
                "stdout_redirection": self.stdout_redirection,
                "stderr_redirection": self.stderr_redirection,
                "stdout_append": self.stdout_append,
                "stderr_append": self.stderr_append,
            }
        )


def process_args(args: str) -> List[Args]:
    return list(
        filter(
            None,
            [process_args_for_one(sub_args.strip()) for sub_args in args.split("|")],
        )
    )


def process_args_for_one(args: str) -> Optional[Args]:
    if not args:
        return None
    inside_single = False
    inside_double = False
    escape = False
    quoted_escape = False
    quoted_escape_characters = {'"', "\\"}
    res = [""]
    for c in args:
        match c:
            case "'" if inside_single:
                inside_single = False
            case "'" if not inside_double and not escape:
                inside_single = True
            case '"' if inside_double and not quoted_escape:
                inside_double = False
            case '"' if not inside_single and not escape and not quoted_escape:
                inside_double = True
            case "\\" if inside_double and not quoted_escape:
                quoted_escape = True
            case _ if inside_single or inside_double:
                if quoted_escape and c not in quoted_escape_characters:
                    res[-1] += "\\"
                quoted_escape = False
                res[-1] += c
            case " " if not escape:
                if res[-1]:
                    res.append("")
            case _:
                if c == "\\" and not escape:
                    escape = True
                else:
                    escape = False
                    res[-1] += c

    if res[-1] == "":
        res.pop()
    cmd = res[0]
    stdout_redirection = None
    stderr_redirection = None
    stdout_append = False
    stderr_append = False
    i = len(res)

    def inner(c):
        i = res.index(c)
        return i, res[i + 1]

    if ">" in res:
        i, stdout_redirection = inner(">")
    elif "1>" in res:
        i, stdout_redirection = inner("1>")
    elif ">>" in res:
        i, stdout_redirection = inner(">>")
        stdout_append = True
    elif "1>>" in res:
        i, stdout_redirection = inner("1>>")
        stdout_append = True
    elif "2>" in res:
        i, stderr_redirection = inner("2>")
    elif "2>>" in res:
        i, stderr_redirection = inner("2>>")
        stderr_append = True
    return Args(
        cmd,
        res[1:i],
        stdout_redirection,
        stderr_redirection,
        stdout_append,
        stderr_append,
    )


def _read() -> List[Args]:
    _in = input("$ ")
    return process_args(_in)


@cache
def _get_external_cmds() -> Dict[str, str]:
    cmds = {}
    for d in os.environ.get("PATH").split(":"):
        if not os.path.exists(d):
            continue
        for cmd in os.listdir(d):
            path = f"{d}/{cmd}"
            if os.access(path, os.X_OK):
                cmds[cmd] = path
    return cmds


def _get_external_cmd(cmd) -> Optional[str]:
    return _get_external_cmds().get(cmd)


def _get_exec(cmd) -> Optional[Callable]:
    return VALID_COMMANDS.get(cmd)


def _evaluate(args: Args) -> int:
    cmd = args.cmd
    cmd_args = args.args
    original_stdout = os.dup(sys.stdout.fileno())
    original_stderr = os.dup(sys.stderr.fileno())
    stdout_file, stderr_file = None, None

    if args.stdout_redirection:
        stdout_file = open(args.stdout_redirection, "a" if args.stdout_append else "w")
        os.dup2(stdout_file.fileno(), sys.stdout.fileno())

    if args.stderr_redirection:
        stderr_file = open(args.stderr_redirection, "a" if args.stderr_append else "w")
        os.dup2(stderr_file.fileno(), sys.stderr.fileno())

    fn = _get_exec(cmd)
    try:
        if fn is not None:
            return fn(*cmd_args)
        path = _get_external_cmd(cmd)
        if path is not None:
            return subprocess.call([cmd, *cmd_args])
        print(f"{cmd}: command not found", file=sys.stderr)
        return 1
    finally:
        os.dup2(original_stdout, sys.stdout.fileno())
        os.dup2(original_stderr, sys.stderr.fileno())
        os.close(original_stdout)
        os.close(original_stderr)
        if stdout_file is not None:
            stdout_file.close()
        if stderr_file is not None:
            stderr_file.close()


def _evaluate_all(all_args: List[Args]) -> int:
    if len(all_args) == 0:
        return 0
    if len(all_args) == 1:
        return _evaluate(all_args[0])

    original_stdin = os.dup(sys.stdin.fileno())
    original_stdout = os.dup(sys.stdout.fileno())

    read_fd, write_fd = os.pipe()
    pid = os.fork()

    if pid > 0:
        os.close(write_fd)
        os.dup2(read_fd, sys.stdin.fileno())
        os.close(read_fd)

        exit_code = _evaluate_all(all_args[1:])
        if exit_code >= 0:
            os.wait()

        os.dup2(original_stdin, sys.stdin.fileno())
        os.close(original_stdin)
        os.close(original_stdout)
        return exit_code
    else:
        os.close(read_fd)
        os.dup2(write_fd, sys.stdout.fileno())
        os.close(write_fd)

        _evaluate(all_args[0])

        os.dup2(original_stdout, sys.stdout.fileno())
        os.close(original_stdin)
        os.close(original_stdout)
        return -1


def autocomplete(text: str, state: int) -> Optional[str]:
    prefix = text.split(" ")[-1]
    options = sorted(
        [cmd for cmd in VALID_COMMANDS | _get_external_cmds() if cmd.startswith(prefix)]
    )

    if state < len(options):
        if len(options) == 1:
            return f"{options[0]} "
        return options[state]

    return None


def repl():
    while True:
        exit_code = _evaluate_all(_read())
        if exit_code == -1:
            break


VALID_COMMANDS = {
    "exit": _exit,
    "echo": _echo,
    "type": _type,
    "pwd": _pwd,
    "cd": _cd,
    "history": _history,
}


def main():
    HISTFILE = os.environ.get("HISTFILE")
    readline.set_completer(autocomplete)
    if "libedit" in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
    if HISTFILE is not None and os.path.exists(HISTFILE):
        _history("-r", HISTFILE)
    repl()
    readline.write_history_file(HISTFILE)


if __name__ == "__main__":
    main()