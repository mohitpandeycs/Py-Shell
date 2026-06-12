import readline
from typing import List
import os

# Global variables
BUILTIN_COMMANDS = ["echo", "exit"]

matchCache: List[str] = []
EXECUTABLE_LIST = []
CURR_LCP: str = ""


def initExecutables() -> None:
    global EXECUTABLE_LIST, BUILTIN_COMMANDS
    paths = os.environ.get("PATH")
    if not paths:
        # not path variables to think about
        EXECUTABLE_LIST = BUILTIN_COMMANDS
        return
    for path in paths.split(":"):
        # skip the path doesnt exist
        if not os.path.exists(path):
            continue
        EXECUTABLE_LIST.extend(os.listdir(path))
    # remove duplicates
    EXECUTABLE_LIST = list(set(BUILTIN_COMMANDS + EXECUTABLE_LIST))


def getLcp() -> str:
    if len(matchCache) < 2:
        return ""
    lcp = ""
    for a in zip(*matchCache):
        if not all(a[idx] == a[idx + 1] for idx in range(0, len(a) - 1)):
            break
        lcp += a[0]
    return lcp


# set tab for completion
def completer(text: str, state: int):
    global matchCache
    lineBuffer = readline.get_line_buffer()

    # File completion
    if len(lineBuffer.split(" ")) > 1:
        if state == 0:
            matchCache.clear()
            matchCache.extend(
                sorted(
                    [file for file in os.listdir(os.getcwd()) if file.startswith(text)]
                )
            )
        return matchCache[state] + " " if state < len(matchCache) else None

    # command completions
    else:
        # readline calls the completer function multiple times with the state 0,1,2
        if state == 0:
            matchCache.clear()
            matchCache.extend(
                sorted(
                    [command for command in EXECUTABLE_LIST if command.startswith(text)]
                )
            )
            LCP = getLcp()
            # if LCP exists then complete and clear the match cache
            if LCP and LCP != text:
                matchCache.clear()
                return LCP

        return matchCache[state] + " " if state < len(matchCache) else None