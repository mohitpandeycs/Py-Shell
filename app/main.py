import cmd
import sys
import os
import subprocess
import shlex
import readline


BUILTINS = {"echo", "exit", "type", "pwd", "cd", "complete"}


def handle_echo(args):
    print(" ".join(args))


def handle_exit(args):
    sys.exit(0)


def handle_type(args):
    if not args:
        return
    cmd = args[0]
    if cmd in BUILTINS:
        print(f"{cmd} is a shell builtin")
        return

    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    for directory in path_dirs:
        full_path = os.path.join(directory, cmd)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            print(f"{cmd} is {full_path}")
            return

    print(f"{cmd}: not found")


def find_executable(cmd):
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    for directory in path_dirs:
        full_path = os.path.join(directory, cmd)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    return None


def handle_cd(args):
    if not args:
        return
    path = args[0]
    if path == "~":
        path = os.environ.get("HOME", "")
    try:
        os.chdir(path)
    except FileNotFoundError:
        print(f"cd: {path}: No such file or directory")


def handle_complete(args):
    if len(args) >= 2 and args[0] == "-p":
        print(f"complete: {args[1]}: no completion specification", file=sys.stderr)


commands = {
    "echo": handle_echo,
    "exit": handle_exit,
    "type": handle_type,
    "pwd": lambda args: print(os.getcwd()),
    "cd": handle_cd,
    "complete": handle_complete,
}


def get_redirect(parts):
    stdout_file = None
    stdout_mode = "w"
    stderr_file = None
    stderr_mode = "w"
    clean = []
    i = 0
    while i < len(parts):
        if parts[i] in (">", "1>"):
            if i + 1 < len(parts):
                stdout_file = parts[i + 1]
                stdout_mode = "w"
                i += 2
            else:
                i += 1
        elif parts[i] in (">>", "1>>"):
            if i + 1 < len(parts):
                stdout_file = parts[i + 1]
                stdout_mode = "a"
                i += 2
            else:
                i += 1
        elif parts[i] == "2>":
            if i + 1 < len(parts):
                stderr_file = parts[i + 1]
                stderr_mode = "w"
                i += 2
            else:
                i += 1
        elif parts[i] == "2>>":
            if i + 1 < len(parts):
                stderr_file = parts[i + 1]
                stderr_mode = "a"
                i += 2
            else:
                i += 1
        else:
            clean.append(parts[i])
            i += 1
    return clean, stdout_file, stdout_mode, stderr_file, stderr_mode


def get_executables(prefix):
    matches = set()
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    for directory in path_dirs:
        try:
            for name in os.listdir(directory):
                if name.startswith(prefix):
                    full_path = os.path.join(directory, name)
                    if os.access(full_path, os.X_OK):
                        matches.add(name)
        except OSError:
            continue
    return sorted(matches)


def longest_common_prefix(strings):
    if not strings:
        return ""
    prefix = strings[0]
    for s in strings[1:]:
        while not s.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    return prefix


_tab_state = {"last_text": None, "count": 0}


def completer(text, state):
    line = readline.get_line_buffer()

    if " " in line:
        prefix = line.split(" ")[-1]

        if "/" in prefix:
            dir_path, file_prefix = prefix.rsplit("/", 1)
            search_dir = dir_path + "/"
        else:
            dir_path = "."
            file_prefix = prefix
            search_dir = ""

        try:
            files = sorted(f for f in os.listdir(dir_path) if f.startswith(file_prefix))
        except OSError:
            files = []

        if not files:
            if state == 0:
                sys.stdout.write("\x07")
                sys.stdout.flush()
            return None

        if len(files) == 1:
            if state == 0:
                match = search_dir + files[0]
                full_path = os.path.join(dir_path, files[0])
                suffix = "/" if os.path.isdir(full_path) else " "
                return match + suffix
            return None

        # Multiple matches — try LCP
        lcp = longest_common_prefix(files)

        if lcp != file_prefix:
            if state == 0:
                _tab_state["last_text"] = search_dir + lcp
                return search_dir + lcp
            return None

        # Already at LCP boundary — bell then list
        if text != _tab_state["last_text"]:
            _tab_state["last_text"] = text
            _tab_state["count"] = 0

        if state == 0:
            _tab_state["count"] += 1
            if _tab_state["count"] == 1:
                sys.stdout.write("\x07")
                sys.stdout.flush()
            elif _tab_state["count"] >= 2:
                display = []
                for f in files:
                    full_path = os.path.join(dir_path, f)
                    display.append(f + "/" if os.path.isdir(full_path) else f)
                sys.stdout.write("\n" + "  ".join(display) + "\n")
                sys.stdout.write("$ " + line)
                sys.stdout.flush()
                _tab_state["count"] = 0
        return None

    # Command name completion
    matches = sorted(
        set([cmd for cmd in BUILTINS if cmd.startswith(text)] + get_executables(text))
    )

    if text != _tab_state["last_text"]:
        _tab_state["last_text"] = text
        _tab_state["count"] = 0

    if not matches:
        if state == 0:
            sys.stdout.write("\x07")
            sys.stdout.flush()
        return None

    if len(matches) == 1:
        if state == 0:
            return matches[0] + " "
        return None

    # Multiple command matches — try LCP
    lcp = longest_common_prefix(matches)

    if lcp != text:
        if state == 0:
            _tab_state["last_text"] = lcp
            return lcp
        return None

    if state == 0:
        _tab_state["count"] += 1
        if _tab_state["count"] == 1:
            sys.stdout.write("\x07")
            sys.stdout.flush()
        elif _tab_state["count"] >= 2:
            sys.stdout.write("\n" + "  ".join(matches) + "\n")
            sys.stdout.write("$ " + text)
            sys.stdout.flush()
            _tab_state["count"] = 0
    return None


readline.set_completer(completer)
readline.parse_and_bind("tab: complete")
readline.set_completer_delims(" \t\n")


def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()

        user_input = input()
        parts = shlex.split(user_input)

        if not parts:
            continue

        parts, stdout_file, stdout_mode, stderr_file, stderr_mode = get_redirect(parts)
        if not parts:
            continue

        cmd, *args = parts

        out = open(stdout_file, stdout_mode) if stdout_file else None
        err = open(stderr_file, stderr_mode) if stderr_file else None
        try:
            if cmd in commands:
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                if out:
                    sys.stdout = out
                if err:
                    sys.stderr = err
                commands[cmd](args)
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            else:
                full_path = find_executable(cmd)
                if full_path:
                    subprocess.run(
                        [cmd] + args, executable=full_path, stdout=out, stderr=err
                    )
                else:
                    print(f"{cmd}: command not found")
        finally:
            if out:
                out.close()
            if err:
                err.close()


if __name__ == "__main__":
    main()