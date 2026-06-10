import sys
import os
import shlex
import subprocess


def main():
    prompt = "$ "
    while True:
        command = input(prompt)
        argv = shlex.split(command)
        handler = get_command_handler(argv)
        handler(argv)


def get_command_handler(argv):
    name = "builtin_" + argv[0]
    func = globals().get(name, None)
    if func is not None:
        handler = BuiltinHandler(func)
    else:
        path = find_executable(argv[0])
        if path is not None:
            handler = ExecutableHandler(path)
        else:
            handler = CommandNotFoundHandler()
    return handler


def find_executable(name):
    for d in os.get_exec_path():
        path = os.path.join(d, name)
        if os.access(path, os.X_OK):
            return path
    return None


class CommandNotFoundHandler:
    def __call__(self, argv):
        print(f"{argv[0]}: command not found", file=sys.stderr)

    def get_type_message(self, argv):
        command = argv[0]
        return f"{command}: not found"


class BuiltinHandler:
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def get_type_message(self, argv):
        command = argv[0]
        return f"{command} is a shell builtin"


class ExecutableHandler:
    def __init__(self, path):
        self.path = path

    def __call__(self, argv):
        subprocess.run(
            argv,
            executable=self.path,
        )

    def get_type_message(self, argv):
        command = argv[0]
        return f"{command} is {self.path}"


def builtin_exit(argv, **kw):
    exit(0)


def builtin_echo(argv, **kw):
    print(" ".join(argv[1:]))


def builtin_type(argv, **kw):
    if len(argv) < 2:
        return

    argv = argv[1:]
    handler = get_command_handler(argv)
    print(handler.get_type_message(argv))


def builtin_pwd(argv, **kw):
    print(os.getcwd())


def builtin_cd(argv, **kw):
    if len(argv) < 2:
        return
    path = argv[1]
    path = os.path.expanduser(path)
    try:
        os.chdir(path)
    except FileNotFoundError:
        print(f"cd: {argv[1]}: No such file or directory")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit(1)