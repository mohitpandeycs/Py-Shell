import subprocess
from typing import List, Dict, Literal, Optional
import os

BUILTIN_COMMANDS = ["exit", "echo", "type", "pwd", "cd", "complete", "jobs", "history"]
HISTORY: List[str] = []
PREV_DIR: str = ""
# PATH_TO_COMPLETION = "/home/zora/personal/dev/codecrafters-shell-python"
# completionData = PATH_TO_COMPLETION + "/app/completion_data.json"
COMPLETION_PATHS: Dict[str, str] = {}
BACKGROUND_PROCESS: list = []


def initShellVars():
    global PREV_DIR, COMPLETION_PATHS
    PREV_DIR = os.getcwd()

    # if os.path.isfile(completionData):
    #     with open(completionData, "r") as f:
    #         COMPLETION_PATHS = json.load(f)
    #     f.close()
    # else:
    #     Path(completionData).touch(exist_ok=True)


# def postShellOps():
#     with open(completionData, "w") as f:
#         json.dump(COMPLETION_PATHS, f, indent=2)
#     f.close()


# def reapJobsMain():
#     global BACKGROUND_PROCESS
#     for idx, processInfo in enumerate(BACKGROUND_PROCESS.copy()):
#         if processInfo[-2] == "Done":
#             BACKGROUND_PROCESS[idx] = None
#             continue
#
#         process = processInfo[-1]
#         returnCode = process.poll()
#
#         if returnCode is not None:
#             BACKGROUND_PROCESS[idx][-2] = "Done"
#             # reap :read the return status and remove it from the table
#             process.wait()
#
#             print(
#                 str(
#                     f"[{processInfo[0]}]"
#                     + str(processInfo[-1])
#                     + f"  {processInfo[3]}"
#                     + " " * (17 if processInfo[3] == "Running" else 16)
#                     + processInfo[2]
#                     + (" &" if processInfo[3] == "Running" else "")
#                 )
#             )
#
#     # Filter: remove the None
#     BACKGROUND_PROCESS = [
#         processInfo for processInfo in BACKGROUND_PROCESS if processInfo is not None
#     ]


# utils
def findExeFiles(arg: str) -> str:
    # os.pathsep is a string for the sep
    # : is Unix
    # ; is Windows
    PATH = os.environ.get("PATH", "")
    for path in PATH.split(os.pathsep):
        # check if the path exists in the os
        # if doesnt move to the next PATH in the list
        if not os.path.exists(path):
            continue
        # check if the command matches a file name
        if arg in os.listdir(path):
            fullPath = path + f"/{arg}"
            # check if it is executable
            if os.access(fullPath, os.X_OK):
                return fullPath
    return ""


def echo(args: List[str]):
    # remove the "" when spliting "Hello  World" => ["Hello","","World"]
    return " ".join([arg for arg in args if arg != ""])
    # print(" ".join([arg for arg in args if arg != ""]))


def pwd():
    return os.getcwd()
    # print(os.getcwd())


def cd(args: List[str]) -> str:
    global PREV_DIR
    if len(args) > 1:
        print("cd: Error: more than one argument passed")
    # Handle the home dir
    dirPath = args[0] if len(args) != 0 else ""
    if dirPath == "":
        dirPath = os.environ.get("HOME", "")
    if dirPath.startswith("~"):
        homeDir = os.environ.get("HOME", "")
        dirPath = dirPath.replace("~", homeDir, 1)
    if dirPath.startswith("-"):
        dirPath = PREV_DIR
    try:
        currDir = os.getcwd()
        # handles abs and relative on its own
        os.chdir(dirPath)
        # if changed properly change the PREV_DIR
        PREV_DIR = currDir
        return ""
    except (FileNotFoundError, PermissionError, NotADirectoryError) as e:
        return f"cd: {dirPath}: {e.strerror}"


def typeCommand(args: List[str]):
    for arg in args:
        # if builtin
        if arg in BUILTIN_COMMANDS:
            # print(f"{arg} is a shell builtin")
            return f"{arg} is a shell builtin"

        # check if in the user path
        elif path := findExeFiles(arg):
            return f"{arg} is {path}"
        else:
            # print(f"{arg}: not found")
            return f"{arg}: not found"


def complete(args: List[str]):
    # handle the flag
    if args[0] == "-p":
        for command in args[1:]:
            if command in COMPLETION_PATHS:
                print(f"complete -C '{COMPLETION_PATHS.get(command, '')}' {command}")
            else:
                # print the error for now
                print(f"complete: {command}: no completion specification")
    elif args[0] == "-C":
        try:
            path = args[1].strip(" ")
        except Exception:
            print("need path of completer")
            return
        try:
            commandName = args[2].strip(" ")
        except Exception:
            print("need the name of command register")
            return
        # adding the command name to the path
        COMPLETION_PATHS[commandName] = path
    elif args[0] == "-r":
        try:
            command = args[1].strip(" ")
        except Exception:
            print("need the name of command to remove")
            return
        COMPLETION_PATHS.pop(command)


def jobs(args: List[str], mode: Literal["auto", "manual"] = "manual"):
    # Poll the existing jobs to see if they ended
    # remove them
    global BACKGROUND_PROCESS
    for idx, processInfo in enumerate(BACKGROUND_PROCESS):
        if processInfo[-2] == "Done":
            BACKGROUND_PROCESS[idx] = None
            continue

        process = processInfo[-1]
        returnCode = process.poll()

        if returnCode is not None:
            BACKGROUND_PROCESS[idx][-2] = "Done"
            # reap :read the return status and remove it from the table
            process.wait()
    # Filter: remove the None
    BACKGROUND_PROCESS = [
        processInfo for processInfo in BACKGROUND_PROCESS if processInfo is not None
    ]

    if not args:
        # Hardcoded to one for now
        if not BACKGROUND_PROCESS:
            return
        output = []
        # Adding + and - to the last and second processs
        for idx in range(-1, -len(BACKGROUND_PROCESS) - 1, -1):
            processInfo = BACKGROUND_PROCESS[idx].copy()
            if idx == -1:
                processInfo.append("+")
            elif idx == -2:
                processInfo.append("-")
            else:
                processInfo.append(" ")
            output.append(processInfo)

        # sorting based on the id
        output.sort(key=lambda x: x[0])

        for idx, processInfo in enumerate(output):
            if mode == "auto" and processInfo[3] == "Running":
                output[idx] = None
                continue

            output[idx] = str(
                f"[{processInfo[0]}]"
                + str(processInfo[-1])
                + f"  {processInfo[3]}"
                + " " * (17 if processInfo[3] == "Running" else 16)
                + processInfo[2]
                + (" &" if processInfo[3] == "Running" else "")
            )
        output = [process for process in output if process]
        if output:
            print("\n".join(output))
        # dont why i did this but okie
        del output
        return
    else:
        currId = 1
        for processInfo in BACKGROUND_PROCESS:
            if processInfo[0] != currId:
                break
            currId += 1
        process = subprocess.Popen(args)
        pid = process.pid
        BACKGROUND_PROCESS.append(
            [
                currId,
                str(pid),
                " ".join(args),
                "Running",
                process,
            ]
        )
        print(f"[{currId}] {pid}")


def history(args: Optional[List[str]]):
    n = len(HISTORY)

    if args and args[0].isnumeric():
        n = int(args[0])

    startIdx = len(HISTORY) - n
    for idx in range(startIdx, len(HISTORY)):
        line = HISTORY[idx]
        print(f"    {idx + 1}  {line}")
