import os
import shlex
import subprocess
import shutil
import sys
import readline
from contextlib import redirect_stdout, redirect_stderr, nullcontext
from pathlib import Path


def parse_input(user_input):
    command_with_args = shlex.split(user_input)

    if "|" in command_with_args:
        return {
            "type": "pipeline",
            "commands": parse_pipeline(command_with_args),
        }

    stderr_file = None
    stdout_file = None
    stdout_mode = "w"
    stderr_mode = "w"
    args = []

    i = 0
    while i < len(command_with_args):
        tok = command_with_args[i]

        match tok:
            case ">" | "1>":
                stdout_file = command_with_args[i + 1]
                i += 2
            case ">>" | "1>>":
                stdout_file = command_with_args[i + 1]
                stdout_mode = "a"
                i += 2
            case "2>":
                stderr_file = command_with_args[i + 1]
                i += 2
            case "2>>":
                stderr_file = command_with_args[i + 1]
                stderr_mode = "a"
                i += 2
            case _:
                args.append(tok)
                i += 1

    return {
        "type": "simple",
        "command": args,
        "stdout": (stdout_file, stdout_mode),
        "stderr": (stderr_file, stderr_mode),
    }


def parse_pipeline(command_with_args):
    commands = []
    current = []
    for token in command_with_args:
        if token == "|":
            if not current:
                raise ValueError("invalid pipeline")
            commands.append(current)
            current = []
        else:
            current.append(token)

    if not current:
        raise ValueError("invalid pipeline")

    commands.append(current)
    return commands


def run_pipeline(commands):
    processes = []
    prev_pipe_r = None

    for i, cmd in enumerate(commands):
        old_stdin = sys.stdin
        old_stdout = sys.stdout

        if i == len(commands) - 1:
            stdout_target = None
        else:
            pipe_r, pipe_w = os.pipe()
            stdout_target = os.fdopen(pipe_w, "w")

        stdin_target = os.fdopen(prev_pipe_r, "r") if prev_pipe_r is not None else None

        try:
            if cmd[0] in BUILTINS:
                if stdin_target:
                    sys.stdin = stdin_target
                if stdout_target:
                    sys.stdout = stdout_target
                BUILTINS[cmd[0]](*cmd[1:])
            elif shutil.which(cmd[0]):
                process = subprocess.Popen(
                    cmd,
                    stdin=stdin_target,
                    stdout=stdout_target if stdout_target else sys.stdout,
                    stderr=sys.stderr,
                )
                processes.append(process)
            else:
                print(f"{cmd[0]}: command not found", file=sys.stderr)
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

        if stdin_target:
            stdin_target.close()
        if stdout_target:
            stdout_target.close()

        prev_pipe_r = pipe_r if i != len(commands) - 1 else None

    for process in processes:
        process.wait()


def run(command_with_args, stdout, stderr):
    command, *args = command_with_args
    stdout_file, stdout_mode = stdout
    stderr_file, stderr_mode = stderr
    if command in BUILTINS:
        run_command(
            BUILTINS[command], args, stdout_file, stdout_mode, stderr_file, stderr_mode
        )
    elif shutil.which(command):
        if stdout_file or stderr_file:
            with (
                open(stdout_file, stdout_mode) if stdout_file else nullcontext() as out,
                open(stderr_file, stderr_mode) if stderr_file else nullcontext() as err,
            ):
                subprocess.run([command] + args, stdout=out, stderr=err)
        else:
            subprocess.run([command] + args)
    else:
        print(f"{command}: command not found")


def run_command(func, args, stdout_file, stdout_mode, stderr_file, stderr_mode):
    if stdout_file or stderr_file:
        with (
            open(stdout_file, stdout_mode) if stdout_file else nullcontext() as out,
            open(stderr_file, stderr_mode) if stderr_file else nullcontext() as err,
            redirect_stdout(out) if stdout_file else nullcontext(),
            redirect_stderr(err) if stderr_file else nullcontext(),
        ):
            func(*args)
    else:
        func(*args)


def type_cmd(command):
    if command in BUILTINS:
        print(f"{command} is a shell builtin")
    elif path := shutil.which(command):
        print(f"{command} is {path}")
    else:
        print(f"{command}: not found")


def cd_cmd(args):
    try:
        if args == "~":
            os.chdir(Path.home())
        else:
            os.chdir(args)
    except:
        print(f"cd: {args}: No such file or directory")


def history_cmd(arg1=None, arg2=None):
    if arg2 and arg1 == "-r":
        file = arg2
        readline.read_history_file(file)
        return

    length = readline.get_current_history_length()
    limit = length

    if arg1 is not None:
        limit = int(arg1)

    start = max(1, length - limit + 1)
    for i in range(start, length + 1):
        print(f"   {i}  {readline.get_history_item(i)}")


def get_all_executables():
    paths = os.environ.get("PATH", "").split(os.pathsep)
    executables = set()
    for p in paths:
        if os.path.isdir(p):
            for f in os.listdir(p):
                fp = os.path.join(p, f)
                if os.path.isfile(fp) and os.access(fp, os.X_OK):
                    executables.add(f)
    return executables


def get_longest_common_prefix(strings):
    if not strings:
        return ""
    if len(strings) == 1:
        return strings[0]

    prefix = strings[0]
    for string in strings[1:]:
        length = 0
        for i, (c1, c2) in enumerate(zip(prefix, string)):
            if c1 != c2:
                break
            length = i + 1
        prefix = prefix[:length]
        if not prefix:
            break

    return prefix


all_commands = get_all_executables()
BUILTINS = {
    "exit": lambda: sys.exit(0),
    "echo": lambda *args: print(" ".join(args)),
    "type": type_cmd,
    "pwd": lambda: print(os.getcwd()),
    "cd": cd_cmd,
    "history": history_cmd,
}


def main():
    last_tab_text = ""
    last_tab_matches = []
    last_tab_count = 0

    def completer(text, state):
        nonlocal last_tab_text, last_tab_matches, last_tab_count

        line = readline.get_line_buffer()

        if not line.strip() or " " not in line.lstrip():
            if text != last_tab_text:
                last_tab_text = text
                last_tab_matches = [
                    c
                    for c in set(list(BUILTINS.keys()) + list(all_commands))
                    if c.startswith(text)
                ]
                last_tab_count = 0

            if not last_tab_matches:
                return None

            if len(last_tab_matches) == 1:
                if state == 0:
                    return last_tab_matches[0] + " "
                return None

            if last_tab_count == 0:
                last_tab_count += 1
                if state == 0:
                    sys.stdout.write("\a")  # Ring bell
                    sys.stdout.flush()

                    longest_prefix = get_longest_common_prefix(last_tab_matches)
                    if len(longest_prefix) > len(text) and state == 0:
                        return longest_prefix
                    return text
                return None
            else:
                if state == 0:
                    print()  # New line
                    print("  ".join(sorted(last_tab_matches)))
                    sys.stdout.write(f"$ {text}")
                    sys.stdout.flush()
                    return None

                longest_prefix = get_longest_common_prefix(last_tab_matches)
                if len(longest_prefix) > len(text) and state == 0:
                    return longest_prefix

                return None
        return None

    def setup_readline():
        if "libedit" in readline.__doc__:
            readline.parse_and_bind("bind ^I rl_complete")
        else:
            readline.parse_and_bind("tab: complete")
        readline.set_completer(completer)
        readline.set_completer_delims(" \t\n")
        readline.parse_and_bind("set show-all-if-ambiguous off")
        readline.parse_and_bind("set completion-query-items -1")

    setup_readline()
    while True:
        try:
            user_input = input("$ ").strip()

            parsed = parse_input(user_input)

            if parsed["type"] == "pipeline":
                run_pipeline(parsed["commands"])
            else:
                run(parsed["command"], parsed["stdout"], parsed["stderr"])

        except KeyboardInterrupt:
            print()
        except Exception as e:
            print(e)


if __name__ == "__main__":
    main()
