import sys
import os
from pathlib import Path
import subprocess
from typing import Literal, List
import readline

from app.compeletion import completer, initExecutables
from app.builtin import (
    cd,
    jobs,
    # postShellOps,
    pwd,
    echo,
    typeCommand,
    initShellVars,
    findExeFiles,
    complete,
    HISTORY,
    history,
)

# from builtin import (
#     HISTORY,
#     cd,
#     complete,
#     history,
#     pwd,
#     echo,
#     typeCommand,
#     initShellVars,
#     findExeFiles,
#     # postShellOps,
#     jobs,
# )
# from compeletion import completer, initExecutables

errorBuffer: str = ""
outputBuffer: str = ""
# the list of supported builtin commands by the shell
BUILTIN_COMMANDS = {
    "exit": lambda ctx: sys.exit(0),
    "echo": lambda ctx: echo(ctx["args"]),
    "type": lambda ctx: typeCommand(ctx["args"]),
    "pwd": lambda ctx: pwd(),
    "cd": lambda ctx: cd(ctx["args"]),
    "complete": lambda ctx: complete(ctx["args"]),
    "jobs": lambda ctx: jobs(ctx["args"]),
    "history": lambda ctx: history(ctx["args"]),
}


def createFile(filePath: str):
    # if already present do nothing
    if os.path.isfile(filePath):
        return
    # deal with honme directory
    if filePath.startswith("~"):
        homeDir = os.environ.get("HOME", "")
        filePath = filePath.replace("~", homeDir, 1)
    # create the file
    Path(filePath).touch(exist_ok=True)


def runCommand(command: str, args: List[str]):
    global errorBuffer, outputBuffer
    if args and args[-1] == "&":
        args.pop()
        args = [command] + args
        command = "jobs"
    # check if the command is a builtin command and run it
    if command in BUILTIN_COMMANDS:
        ctx = {
            "args": args,
        }
        outputBuffer = BUILTIN_COMMANDS[command](ctx)

    # check if the command is an executable in the path
    elif findExeFiles(command) or os.access(command, os.X_OK):
        result = subprocess.run([command] + args, capture_output=True)
        errorBuffer = result.stderr.decode().lstrip(" ").rstrip("\n")
        outputBuffer = result.stdout.decode().lstrip(" ").rstrip("\n")
    else:
        # TODO: implement the command checking
        outputBuffer = f"{command}: command not found"


def redirectCommand(
    command: str,
    args: List[str],
    redirectChar: str,
    mode: Literal["w", "a"],
    typeOf: Literal["error", "output"],
):
    filePath = args[args.index(redirectChar) + 1]
    # create the file
    try:
        createFile(filePath)
    except (FileNotFoundError, PermissionError, IsADirectoryError, OSError) as e:
        print(f"{e.strerror}: {e.filename}")
        return
    except Exception as e:
        print(e)

    # run the command whose output we need
    commandArgs = args[: args.index(redirectChar)]
    try:
        runCommand(command, commandArgs)
    except Exception as e:
        print(f"Error executing commands(redirection):{e}")
        return 1
    # assign the output buffer
    if typeOf == "error":
        writeBuffer = errorBuffer
        printBuffer = outputBuffer
    else:
        writeBuffer = outputBuffer
        printBuffer = errorBuffer

    # adds new line in no empty
    if writeBuffer:
        writeBuffer += "\n"

    # write into the file
    with open(filePath, mode) as f:
        f.write(writeBuffer)
    if printBuffer:
        print(printBuffer)


def splitCommand(commandLine: str) -> tuple[str, List[str]]:
    mode: Literal["UNQUOTED", "SINGLE_QUOTED", "DOUBLE_QUOTED"] = "UNQUOTED"
    currArgs = ""
    args = []

    idx = 0
    while idx < len(commandLine):
        char = commandLine[idx]
        # for char in commandLine:
        if mode == "UNQUOTED":
            if char == "'":
                mode = "SINGLE_QUOTED"
            elif char == '"':
                mode = "DOUBLE_QUOTED"
            elif char == " ":
                args.append(currArgs)
                currArgs = ""
            elif char == "\\":
                # move to next char
                idx += 1
                # make sure not out of index
                if (idx) >= len(commandLine):
                    continue
                escapedChar = commandLine[idx]
                currArgs += escapedChar
            else:
                currArgs += char
        elif mode == "SINGLE_QUOTED":
            if char == "'":
                mode = "UNQUOTED"
            else:
                currArgs += char
        elif mode == "DOUBLE_QUOTED":
            if char == '"':
                mode = "UNQUOTED"
            elif char == "\\":
                # move to next char
                idx += 1
                # make sure not out of index
                if (idx) >= len(commandLine):
                    continue
                escapedChar = commandLine[idx]
                # for now handles only " and \
                if escapedChar in ['"', "\\"]:
                    currArgs += escapedChar
            else:
                currArgs += char
        idx += 1
    if currArgs:
        args.append(currArgs)
    return args[0], args[1:]


def main():
    # To create the REPL loop
    while True:
        # dirName = os.getcwd().split("/")[-1]
        # sys.stdout.write(f"[{dirName}]$ ")
        # sys.stdout.write("$ ")
        # commandline
        commandLine = [arg for arg in input("$ ").strip(" ").split(" ")]
        # TODO:add command + args to history
        HISTORY.append(" ".join(commandLine))

        # # split the command and the args
        # command = commandLine[0]
        # Implementing parsing of '' and ""
        if (
            "'" in " ".join(commandLine)
            or '"' in " ".join(commandLine)
            or "\\" in " ".join(commandLine)
        ):
            command, args = splitCommand(" ".join(commandLine))
        else:
            # split the command and the args
            command = commandLine[0]
            args = [arg for arg in commandLine[1:] if arg != ""]

        # normalise the stdout redirect
        for idx, arg in enumerate(args):
            if arg == "1>":
                args[idx] = ">"
            elif arg == "1>>":
                args[idx] = ">>"
        # redirection
        # stdout out redirection
        if ">" in args:
            redirectCommand(command, args, ">", "w", "output")
        elif ">>" in args:
            redirectCommand(command, args, ">>", "a", "output")
        # stdout error redirection
        elif "2>" in args:
            redirectCommand(command, args, "2>", "w", "error")
        elif "2>>" in args:
            redirectCommand(command, args, "2>>", "a", "error")
        # run a the command if (singular)
        else:
            try:
                runCommand(command, args)
            except Exception as e:
                # Return there because this is an error in the code
                print(f"Error will executing the commands:{e}")
                return 1
            if errorBuffer:
                print(errorBuffer)
            elif outputBuffer:
                print(outputBuffer)
        jobs([], mode="auto")


if __name__ == "__main__":
    readline.parse_and_bind("tab: complete")
    readline.parse_and_bind("set bell-style audible")
    readline.parse_and_bind("set skip-completed-text on")
    readline.set_completer_delims("' '/")
    # readline.parse_and_bind("set editing-mode vi")
    # readline.parse_and_bind("set visible-stats on")
    # readline.parse_and_bind("set show-mode-in-prompt on")
    readline.set_completer(completer)
    initExecutables()
    initShellVars()
    try:
        main()
    except KeyboardInterrupt:
        pass
    # finally:
    # postShellOps()
