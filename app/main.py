import sys
import os
import subprocess
import shlex

builtins = ["exit", "echo", "type", "pwd", "cd"]


def main():
    while True:
        sys.stdout.write("$ ")

        args = shlex.split(input())
        command = args[0]

        if command in builtins:
            if command == "exit":
                break

            if command == "echo":
                print(" ".join(args[1:]))
                continue

            if command == "type":
                command_type = args[1]

                if command_type in builtins:
                    print(f"{command_type} is a shell builtin")
                    continue

                found = False
                paths = os.environ.get("PATH", "").split(os.pathsep)
                for path in paths:
                    full_path = os.path.join(path, command_type)
                    if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                        print(f"{command_type} is {full_path}")
                        found = True
                        break

                if not found:
                    print(f"{command_type}: not found")
                continue

            if command == "pwd":
                print(os.getcwd())
                continue

            if command == "cd":
                path = args[1]

                if path == "~":
                    path = os.getenv("HOME")

                if not os.path.exists(path):
                    print(f"cd: {path}: No such file or directory")
                    continue

                os.chdir(path)
                continue
        else:
            found = False
            paths = os.environ.get("PATH", "").split(os.pathsep)
            for path in paths:
                full_path = os.path.join(path, command)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    subprocess.run(args)
                    found = True
                    break
            if found:
                continue

        print(f"{command}: command not found")


if __name__ == "__main__":
    main()