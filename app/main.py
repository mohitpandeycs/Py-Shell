import os
import sys
import subprocess
import shlex
import readline

BUILTINS = {"echo", "exit", "type", "pwd", "cd"}
BUILTIN_COMPLETIONS = sorted(BUILTINS)


def find_executable(command):
    path_env = os.environ.get("PATH", "")

    for directory in path_env.split(os.pathsep):
        full_path = os.path.join(directory, command)

        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path

    return None


def get_executables():
    executables = set()

    path_env = os.environ.get("PATH", "")

    for directory in path_env.split(os.pathsep):
        if not os.path.isdir(directory):
            continue

        try:
            for file in os.listdir(directory):
                full_path = os.path.join(directory, file)

                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    executables.add(file)

        except OSError:
            pass

    return executables


def completer(text, state):
    line = readline.get_line_buffer()

    # Split the current line
    words = line.split()

    # Completing the command itself (first word)
    if len(words) <= 1 and not line.endswith(" "):
        commands = BUILTIN_COMPLETIONS + list(get_executables())

        matches = sorted(cmd for cmd in set(commands) if cmd.startswith(text))
    else:
        try:
            matches = sorted(f for f in os.listdir(".") if f.startswith(text))
        except OSError:
            matches = []

    if state >= len(matches):
        return None

    match = matches[state]

    # For a single match add a trailing space
    if len(matches) == 1:
        return match + " "

    return match


def main():
    readline.parse_and_bind("tab: complete")
    readline.set_completer(completer)

    while True:
        command = input("$ ")

        stdout_file = None
        stderr_file = None

        stdout_mode = "w"
        stderr_mode = "w"

        parts = shlex.split(command)

        # Handle stdout redirection (> and 1>)
        if ">" in parts:
            idx = parts.index(">")
            stdout_file = parts[idx + 1]
            parts = parts[:idx]

        elif "1>" in parts:
            idx = parts.index("1>")
            stdout_file = parts[idx + 1]
            parts = parts[:idx]

        elif ">>" in parts:
            idx = parts.index(">>")
            stdout_file = parts[idx + 1]
            stdout_mode = "a"
            parts = parts[:idx]

        elif "1>>" in parts:
            idx = parts.index("1>>")
            stdout_file = parts[idx + 1]
            stdout_mode = "a"
            parts = parts[:idx]

        elif "2>>" in parts:
            idx = parts.index("2>>")
            stderr_file = parts[idx + 1]
            stderr_mode = "a"
            parts = parts[:idx]

        # Handle stderr redirection (2>)
        elif "2>" in parts:
            idx = parts.index("2>")
            stderr_file = parts[idx + 1]
            parts = parts[:idx]

        if not parts:
            continue

        # exit builtin
        if parts[0] == "exit":
            break

        # echo builtin
        elif parts[0] == "echo":
            if stderr_file:
                open(stderr_file, stderr_mode).close()
            output = " ".join(parts[1:])

            if stdout_file:
                with open(stdout_file, stdout_mode) as f:
                    print(output, file=f)
            else:
                print(output)

        # pwd builtin
        elif parts[0] == "pwd":
            if stderr_file:
                open(stderr_file, stderr_mode).close()
            output = os.getcwd()

            if stdout_file:
                with open(stdout_file, stdout_mode) as f:
                    print(output, file=f)
            else:
                print(output)

        # cd builtin
        elif parts[0] == "cd":
            directory = parts[1]

            if directory == "~":
                directory = os.getenv("HOME", "")

            try:
                os.chdir(directory)
            except FileNotFoundError:
                print(f"cd: {directory}: No such file or directory")

        # type builtin
        elif parts[0] == "type":
            if stderr_file:
                open(stderr_file, stderr_mode).close()
            cmd = parts[1]

            if cmd in BUILTINS:
                output = f"{cmd} is a shell builtin"
            else:
                executable = find_executable(cmd)

                if executable:
                    output = f"{cmd} is {executable}"
                else:
                    output = f"{cmd}: not found"

            if stdout_file:
                with open(stdout_file, stdout_mode) as f:
                    print(output, file=f)
            else:
                print(output)

        # External commands
        else:
            executable = find_executable(parts[0])

            if executable:
                # stdout redirected
                if stdout_file:
                    with open(stdout_file, stdout_mode) as out:
                        subprocess.run(
                            [parts[0]] + parts[1:], executable=executable, stdout=out
                        )

                # stderr redirected
                elif stderr_file:
                    with open(stderr_file, stderr_mode) as err:
                        subprocess.run(
                            [parts[0]] + parts[1:], executable=executable, stderr=err
                        )

                # no redirection
                else:
                    subprocess.run([parts[0]] + parts[1:], executable=executable)

            else:
                print(f"{command}: command not found")


if __name__ == "__main__":
    main()