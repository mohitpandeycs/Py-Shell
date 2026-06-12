import os
import subprocess
import shlex
import readline

path = os.environ["PATH"]
try:
    home = os.environ["HOME"]
except:
    home = "you're on windows :("
BUILT_IN_COMMANDS = ["exit", "echo", "type", "pwd", "cd"]

AUTOCOMPLETE_ARRAY = BUILT_IN_COMMANDS.copy()

directories = path.split(":")
for directory in directories:
    if os.path.exists(directory):
        dir_list = os.listdir(directory)
        AUTOCOMPLETE_ARRAY += dir_list


def autocomplete(text, state):
    matches = [cmd for cmd in AUTOCOMPLETE_ARRAY if cmd.startswith(text)]
    return matches[state] + " " if state < len(matches) else None


def eval_stdout_overwrite(redirect_symbol: str, command_list: list):
    redirect_stdout_idx = command_list.index(redirect_symbol)
    split_command_segment = command_list[0:redirect_stdout_idx]
    file_segment = command_list[redirect_stdout_idx + 1]
    process = subprocess.Popen(split_command_segment, stdout=subprocess.PIPE)
    out, err = process.communicate()
    with open(file_segment, "wb") as file:
        file.write(out)


def eval_stdout_append(redirect_symbol: str, command_list: list):
    redirect_stdout_idx = command_list.index(redirect_symbol)
    split_command_segment = command_list[0:redirect_stdout_idx]
    file_segment = command_list[redirect_stdout_idx + 1]
    process = subprocess.Popen(split_command_segment, stdout=subprocess.PIPE)
    out, err = process.communicate()
    with open(file_segment, "ab") as file:
        file.write(out)


def is_on_path(command: str):
    directories = path.split(":")
    for directory in directories:
        file_path = f"{directory}/{command}"
        file_exists = os.path.isfile(file_path)
        has_permissions = os.access(file_path, os.X_OK)
        if file_exists and has_permissions:
            return file_path
    return False


def eval_cmd(command: str):
    try:
        split_command = shlex.split(command)
    except ValueError as e:
        print(f"parse error: {e}")
        return

    if not split_command:
        return

    match split_command[0]:
        case "exit":
            exit()

        case "echo":
            if ">" in split_command:
                redirect_stdout_idx = split_command.index(">")
                text_segment = " ".join(split_command[1:redirect_stdout_idx])
                file_segment = split_command[redirect_stdout_idx + 1]
                with open(file_segment, "w") as file:
                    file.write(text_segment + "\n")
            elif "1>" in split_command:
                redirect_stdout_idx = split_command.index("1>")
                text_segment = " ".join(split_command[1:redirect_stdout_idx])
                file_segment = split_command[redirect_stdout_idx + 1]
                with open(file_segment, "w") as file:
                    file.write(text_segment + "\n")
            elif "2>" in split_command:
                redirect_stdout_idx = split_command.index("2>")
                text_segment = " ".join(split_command[1:redirect_stdout_idx])
                file_segment = split_command[redirect_stdout_idx + 1]
                print(text_segment)
                with open(file_segment, "w") as file:
                    file.write("")
            elif ">>" in split_command:
                redirect_stdout_idx = split_command.index(">>")
                text_segment = " ".join(split_command[1:redirect_stdout_idx])
                file_segment = split_command[redirect_stdout_idx + 1]
                with open(file_segment, "a") as file:
                    file.write(text_segment + "\n")
            elif "1>>" in split_command:
                redirect_stdout_idx = split_command.index("1>>")
                text_segment = " ".join(split_command[1:redirect_stdout_idx])
                file_segment = split_command[redirect_stdout_idx + 1]
                with open(file_segment, "a") as file:
                    file.write(text_segment + "\n")
            elif "2>>" in split_command:
                redirect_stdout_idx = split_command.index("2>>")
                text_segment = " ".join(split_command[1:redirect_stdout_idx])
                file_segment = split_command[redirect_stdout_idx + 1]
                print(text_segment)
                with open(file_segment, "a") as file:
                    file.write("")
            else:
                print(" ".join(split_command[1:]))

        case "pwd":
            print(os.getcwd())

        case "cd":
            if len(split_command) < 2:
                os.chdir(home)
            elif split_command[1] == "~":
                os.chdir(home)
            elif os.path.exists(split_command[1]):
                os.chdir(split_command[1])
            else:
                print(f"cd: {split_command[1]}: No such file or directory")

        case "type":
            if len(split_command) < 2:
                print(": not found")
                return
            cmd = split_command[1]
            if cmd in BUILT_IN_COMMANDS:
                print(f"{cmd} is a shell builtin")
            elif path := is_on_path(cmd):
                print(f"{cmd} is {path}")
            else:
                print(f"{cmd}: not found")

        case _:
            cmd = split_command[0]
            if is_on_path(cmd):
                if ">" in split_command:
                    eval_stdout_overwrite(">", split_command)
                elif "1>" in split_command:
                    eval_stdout_overwrite("1>", split_command)
                elif "2>" in split_command:
                    redirect_stdout_idx = split_command.index("2>")
                    split_command_segment = split_command[0:redirect_stdout_idx]
                    file_segment = split_command[redirect_stdout_idx + 1]
                    process = subprocess.Popen(
                        split_command_segment, stderr=subprocess.PIPE
                    )
                    out, err = process.communicate()
                    with open(file_segment, "wb") as file:
                        file.write(err)
                elif ">>" in split_command:
                    eval_stdout_append(">>", split_command)
                elif "1>>" in split_command:
                    eval_stdout_append("1>>", split_command)
                elif "2>>" in split_command:
                    redirect_stdout_idx = split_command.index("2>>")
                    split_command_segment = split_command[0:redirect_stdout_idx]
                    file_segment = split_command[redirect_stdout_idx + 1]
                    process = subprocess.Popen(
                        split_command_segment, stderr=subprocess.PIPE
                    )
                    out, err = process.communicate()
                    with open(file_segment, "ab") as file:
                        file.write(err)
                else:
                    subprocess.call(split_command)
            else:
                print(f"{cmd}: command not found")


def main():
    readline.set_completer(autocomplete)
    readline.parse_and_bind("tab: complete")
    while True:
        command: str = input("$ ")
        eval_cmd(command)


if __name__ == "__main__":
    main()