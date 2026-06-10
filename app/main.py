import sys
import os
import shutil
import subprocess
import shlex
import readline

builtins = ["exit", "echo", "type", "pwd", "cd"]
excecutables = []

PATH = os.environ.get("PATH", "").split(os.pathsep)
HOME = os.environ.get("HOME", "")

for path in PATH:
    try:
        for filename in os.listdir(path):
            filepath = os.path.join(path, filename)
            if os.access(filepath, os.X_OK):
                excecutables.append(filename)
    except FileNotFoundError:
        continue


def find_exc(cmd):
    full_path = None

    for path in PATH:
        full_path = f"{path}/{cmd}"
        try:
            if os.access(full_path, os.X_OK):
                return [full_path, True]
        except FileNotFoundError:
            continue

    return [full_path, False]


def autocomplete(text, state):
    matches = [cmd for cmd in builtins + excecutables if cmd.startswith(text)]
    if len(matches) > 2:
        return matches[state]
    else:
        return matches[state] + " " if state < len(matches) else None


def split_redirection(command):
    for index, token in enumerate(command):
        if token in {">", "1>", ">>", "1>>", "2>"}:
            if index + 1 >= len(command):
                return command, None, None

            return command[:index], token, command[index + 1]

    return command, None, None


def commandLine(cwd, command, cmd, args):
    match cmd:
        case "exit":
            sys.exit()

        case "echo":
            return f"{' '.join(args)}\n"

        case "type":
            if args[0] in builtins:
                return f"{args[0]} is a shell builtin\n"
            else:
                type = find_exc(" ".join(args))

                if type[1] == True:
                    return f"{args[0]} is {type[0]}\n"
                else:
                    return f"{args[0]}: not found\n"

        case "pwd":
            return f"{cwd}\n"

        case "cd":
            if args[0] == "~":
                os.chdir(os.environ.get("HOME", ""))
            else:
                try:
                    os.chdir(args[0])
                except FileNotFoundError:
                    return f"cd: {args[0]}: No such file or directory\n"

            return ""

        case "cat":
            result = subprocess.run(command, capture_output=True, text=True)
            return result.stdout

        case "git":
            if args[0] == "test":
                os.system('git commit -am "shell tester"')
                os.system("git push origin master")
            else:
                os.system(f"{cmd} {' '.join(args)}")

            return "\n"

        case _:
            if shutil.which(cmd):
                result = subprocess.run(command, capture_output=True, text=True)
                return result.stdout
            else:
                return f"{cmd}: command not found\n"


def write_redirection_output(filename, operator, output):
    mode = "a" if operator in {">>", "1>>"} else "w"

    with open(filename, mode, encoding="utf-8") as file:
        file.write(output or "")


def main():
    readline.set_completer(autocomplete)  # type: ignore
    readline.parse_and_bind("tab: complete")  # type: ignore

    cwd = os.getcwd()

    sys.stdin.flush()
    original_command = input("$ ")
    command = shlex.split(original_command)

    if not command:
        return

    command, redirection_operator, redirection_file = split_redirection(command)

    cmd = command[0]
    args = command[1:]

    if redirection_operator:
        output = commandLine(cwd, command, cmd, args)
        write_redirection_output(redirection_file, redirection_operator, output)
    else:
        sys.stdout.write(str(commandLine(cwd, command, cmd, args)))


if __name__ == "__main__":
    while True:
        main()