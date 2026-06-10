import sys
import shutil
import subprocess
import os


def main():
    # TODO: Uncomment the code below to pass the first stage
    while True:
        sys.stdout.write("$ ")
        command = input()

        # exit
        if command == "exit":
            break

        # command breakdown
        first_word = command.split()[0]
        second_part = command[len(first_word) + 1 :]

        # echo commands
        if first_word == "echo":
            print(second_part)

        # type commands
        elif first_word == "type":
            builtins = ["echo", "exit", "type", "pwd"]
            if second_part in builtins:
                print(f"{second_part} is a shell builtin")
            elif shutil.which(second_part):
                print(f"{second_part} is {shutil.which(second_part)}")
            else:
                print(f"{second_part} not found")

        elif first_word == "pwd":
            print(f"{os.getcwd()}")

        elif first_word == "cd":
            try:
                os.chdir(second_part)
            except FileNotFoundError:
                print(f"cd: {second_part}: No such file or directory")

        elif shutil.which(first_word):
            subprocess.run([first_word] + command.split()[1:])
        else:
            print(f"{command}: command not found")


if __name__ == "__main__":
    main()