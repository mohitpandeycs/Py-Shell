import os
import shlex
import subprocess
import sys
import sys
from dataclasses import dataclass
from contextlib import contextmanager

_REDIRECT_MAP: dict[str, tuple[str, str]] = {
    ">": ("stdout", "w"),
    "1>": ("stdout", "w"),
    ">>": ("stdout", "a"),
    "1>>": ("stdout", "a"),
    "2>": ("stderr", "w"),
    "2>>": ("stderr", "a"),
}


@dataclass
class RedirectInfo:
    stdout_file: str | None = None
    stdout_mode: str = "w"
    stderr_file: str | None = None
    stderr_mode: str = "w"

    @property
    def has_redirect(self) -> bool:
        return self.stdout_file is not None or self.stderr_file is not None


def extract_redirects(parts: list[str]) -> tuple[list[str], RedirectInfo]:
    cmd_tokens = []
    redirect = RedirectInfo()
    i = 0
    while i < len(parts):
        token = parts[i]
        if token in _REDIRECT_MAP and i + 1 < len(parts):
            target, mode = _REDIRECT_MAP[token]
            if target == "stdout":
                redirect.stdout_file = parts[i + 1]
                redirect.stdout_mode = mode
            else:
                redirect.stderr_file = parts[i + 1]
                redirect.stderr_mode = mode
            i += 2
        else:
            cmd_tokens.append(token)
            i += 1
    return cmd_tokens, redirect


@contextmanager
def apply_redirect(redirect: RedirectInfo):
    stdout = (
        open(redirect.stdout_file, redirect.stdout_mode)
        if redirect.stdout_file
        else None
    )
    stderr = (
        open(redirect.stderr_file, redirect.stderr_mode)
        if redirect.stderr_file
        else None
    )
    old_stdout, old_stderr = sys.stdout, sys.stderr
    try:
        if stdout:
            sys.stdout = stdout
        if stderr:
            sys.stderr = stderr
        yield stdout, stderr
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr
        if stdout:
            stdout.close()
        if stderr:
            stderr.close()


def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()
        line = sys.stdin.readline()

        if not line:
            break
        line = line.strip()
        if not line:
            continue

        parts = shlex.split(line)
        cmd_tokens, redirect = extract_redirects(parts)

        if not cmd_tokens:
            continue

        with apply_redirect(redirect):
            process = subprocess.Popen(
                cmd_tokens,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout_data, stderr_data = process.communicate()
            if stdout_data:
                sys.stdout.write(stdout_data.decode())
            if stderr_data:
                sys.stderr.write(stderr_data.decode())


if __name__ == "__main__":
    main()
