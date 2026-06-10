import os
import subprocess
import sys
from pathlib import Path


# lets refactor this so that each function returns a string for stdout
def echo(args: list) -> str:
    return " ".join(args)


def handle_exit(*args: list) -> None:
    sys.exit()


def type_search(args: list) -> str:
    is_builtin = builtins.get(args[0])
    if is_builtin:
        return f"{args[0]} is a shell builtin"
    else:
        return search_path_directories(args[0])


def search_path_directories(command: str) -> str:
    paths = set(os.environ["PATH"].split(":"))
    for path in paths:
        # print(f'Checking for {command} in {path}')ß
        if os.path.exists(path + "/" + command) and os.access(
            path + "/" + command, os.X_OK
        ):
            return f"{command} is {path + '/' + command}"
    return f"{command}: not found"


def search_and_return_executable(command: str):
    paths = set(os.environ["PATH"].split(":"))
    for path in paths:
        # print(f'Checking for {command} in {path}')ß
        if os.path.exists(path + "/" + command) and os.access(
            path + "/" + command, os.X_OK
        ):
            return path + "/" + command
    return


def print_working_directory(args: list) -> str:
    return os.getcwd()


def change_directory(args: list) -> None:
    if args[0] == "~":
        os.chdir(os.getenv("HOME"))
        return
    new_path = Path(args[0])
    if new_path.exists():
        os.chdir(new_path)
    else:
        print(f"cd: {new_path}: No such file or directory")
    return


builtins = {
    "exit": handle_exit,
    "echo": echo,
    "type": type_search,
    "pwd": print_working_directory,
    "cd": change_directory,
}

redirect_commands = {
    ">": ["w", "stdout"],
    "1>": ["w", "stdout"],
    "2>": ["w", "stderr"],
    ">>": ["a", "stdout"],
    "1>>": ["a", "stdout"],
    "2>>": ["a", "stderr"],
}


def redirect_output(redirect_command: str, logname: str):
    file_writing_type, output_type = redirect_commands[redirect_command]
    log = open(logname, file_writing_type)
    if output_type == "stdout":
        sys.stdout = log
    elif output_type == "stderr":
        sys.stderr = log
    return log


def parse_command(input_statement: str) -> tuple[str, list]:
    commands_and_arguments = input_statement.split(" ")
    command, args = commands_and_arguments[0], commands_and_arguments[1:]
    return command, args


def main() -> None:
    while True:
        input_statement = input("$ ")
        command, args = parse_command(input_statement)
        # logging = False

        redirects = list(set(args) & set(redirect_commands.keys()))
        if len(redirects) > 0:
            log = redirect_output(redirects[0], args[-1])
            args = args[:-2]
        # Keep in mind you could do a set intersection like found = list(set(args) & set(redirect_types))
        # if '>' in args or '1>' in args or '2>' in args:
        #     logging = True
        #     log = open(args[-1], 'w')
        #     if '2>' in args:
        #         sys.stderr = log
        #     else:
        #         sys.stdout = log
        #     args = args[:-2]

        if builtin := builtins.get(command):
            output = builtin(args)
            if output:
                print(output)
        elif search_and_return_executable(command):
            subprocess.run([command, *args], stdout=sys.stdout, stderr=sys.stderr)
        else:
            print(f"{command}: command not found")

        if "log" in locals():
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            log.close()


if __name__ == "__main__":
    main()