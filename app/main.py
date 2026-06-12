import sys
import enum
import os
import pathlib
import stat
import subprocess
import readline
from contextlib import redirect_stdout, redirect_stderr
from collections import deque
from app.custom_exceptions import DirectoryNotFoundException, InvalidStringException
from app.custom_exceptions import (
    TooManyArgumentsException,
    UnexpectedTokenException,
    CompleteNotFoundException,
    InvalidArgumentException,
)

# from app.logger import debug_logger
from app.stub_debug_logger import debug_logger


STDIN_FD = 0
STDOUT_FD = 1
STDERR_FD = 2
READ_FLAG = "r"
WRITE_FLAG = "w"
APPEND_FLAG = "a"
complete_file = "/tmp/.URMOM"


class Commands:
    echo_cmd = "echo"
    exit_cmd = "exit"
    type_cmd = "type"
    pwd_cmd = "pwd"
    cd_cmd = "cd"
    complete_cmd = "complete"
    null_cmd = "NULL"  # used as kind of a null value, not a actual command
    available_commands = [echo_cmd, exit_cmd, type_cmd, pwd_cmd, cd_cmd, complete_cmd]


class Signal:
    exit_signal = "exit_signal"


class Permissions:
    owner = "owner"
    other = "other"
    group = "group"
    read = "read"
    write = "write"
    executable = "executable"


def print_command_not_found(cmd):
    print(f"{cmd}: command not found", file=sys.stderr)


def print_not_found(cmd):
    print(f"{cmd}: not found", file=sys.stderr)


def print_command_fullpath(cmd, path):
    print(f"{cmd} is {path}")


def check_builtin(command) -> bool:
    if command in Commands.available_commands:
        return True
    return False


def check_file_mode(file, permission: str, level: str) -> bool:
    st = os.stat(file)
    if level == Permissions.owner and permission == Permissions.read:
        return bool(st.st_mode & stat.S_IRUSR)
    if level == Permissions.owner and permission == Permissions.write:
        return bool(st.st_mode & stat.S_IWUSR)
    if level == Permissions.owner and permission == Permissions.executable:
        return bool(st.st_mode & stat.S_IXUSR)
    if level == Permissions.group and permission == Permissions.read:
        return bool(st.st_mode & stat.S_IRGRP)
    if level == Permissions.group and permission == Permissions.write:
        return bool(st.st_mode & stat.S_IWGRP)
    if level == Permissions.group and permission == Permissions.executable:
        return bool(st.st_mode & stat.S_IXGRP)
    if level == Permissions.other and permission == Permissions.read:
        return bool(st.st_mode & stat.S_IROTH)
    if level == Permissions.other and permission == Permissions.write:
        return bool(st.st_mode & stat.S_IWOTH)
    if level == Permissions.other and permission == Permissions.executable:
        return bool(st.st_mode & stat.S_IXOTH)
    return False


def get_path_by_completer_command(command: str) -> str:
    with open(complete_file, READ_FLAG) as f:
        file_data = f.read()
        splitted = file_data.split("\n")
        debug_logger.debug(f"Reading file data for {complete_file=}")
        debug_logger.debug(f"File data (split by newline):{splitted}")
        index = splitted.index(command)
        assert index < len(splitted) - 1
        path = splitted[index + 1]
        return path


def remove_from_completer_command(command: str) -> str:
    assert command in completer_commands
    lines = []
    with open(complete_file, READ_FLAG) as f:
        file_data = f.read()
        lines = file_data.split("\n")
    index = lines.index(command)
    assert (
        index < len(lines) - 1
    )  # asserting that format of the file is command\npath\ncommand\npath....
    new_lines = lines[:index] + lines[index + 2 :]
    debug_logger.debug(f"{new_lines=}")
    with open(complete_file, WRITE_FLAG) as f:
        f.write("\n".join(new_lines))
    index = completer_commands.index(command)
    completer_command = completer_commands[:index] + completer_commands[index + 2 :]


def get_all_completer_commands() -> list[str]:
    try:
        with open(complete_file, READ_FLAG) as f:
            file_data = f.read()
            splitted = file_data.split("\n")
            commands = [x for index, x in enumerate(splitted) if index % 2 == 0]
            commands = [x for x in commands if x != ""]
            return commands
    except OSError as E:
        return []


def get_all_system_commands() -> list[str]:
    path = os.environ["PATH"]
    locations = path.split(os.pathsep)
    rv = []
    rv_set = set()
    for location in locations:
        p = pathlib.Path(location)
        if not p.is_dir():
            continue
        files = [f for f in p.iterdir()]
        for file in files:
            file_suffix = str(file).split("/")[-1]
            if file_suffix not in rv_set:
                rv.append(file_suffix)
            rv_set.add(file_suffix)
    return rv


# returns path
def get_command_path(command) -> str:
    path = os.environ["PATH"]
    locations = path.split(os.pathsep)
    for location in locations:
        p = pathlib.Path(location)
        if not p.is_dir():
            continue
        files = [f for f in p.iterdir()]
        for file in files:
            file_suffix = str(file).split("/")[-1]
            if file_suffix != command:
                continue
            if check_file_mode(file, Permissions.executable, Permissions.other):
                return str(file)
    return Commands.null_cmd


# processing complete shell command.
def process_complete(args: list):
    no_flag = None

    class Flags(enum.StrEnum):
        REGISTER_FLAG = "-C"
        PRINT_FLAG = "-p"
        REMOVE_FLAG = "-r"

    FLAGS = {Flags.REGISTER_FLAG, Flags.PRINT_FLAG, Flags.REMOVE_FLAG}
    flag_pos = {}
    flag_args = {}
    max_flag_args_count = {}
    min_flag_args_count = {}
    prev_flag = no_flag
    for flag in list(FLAGS):
        flag_pos[flag] = -float("inf")
        flag_args[flag] = []
    max_flag_args_count[Flags.REGISTER_FLAG] = 2
    min_flag_args_count[Flags.REGISTER_FLAG] = 2
    max_flag_args_count[Flags.PRINT_FLAG] = 1
    min_flag_args_count[Flags.PRINT_FLAG] = 1
    min_flag_args_count[Flags.REMOVE_FLAG] = 1
    max_flag_args_count[Flags.REMOVE_FLAG] = 1

    # throws CompleteNotFoundException if the command after -p is not found
    def perform_action_by_prevflag(flag: str):
        global complete_file
        assert flag in FLAGS
        assert (
            min_flag_args_count[flag]
            <= len(flag_args[flag])
            <= max_flag_args_count[flag]
        )
        debug_logger.debug(f"complete: Performing flag action for {flag=}")
        match flag:
            case Flags.REGISTER_FLAG:
                with open(complete_file, APPEND_FLAG) as f:
                    debug_logger.debug(
                        f"Appending {flag_args[Flags.REGISTER_FLAG][1]} to {complete_file=}"
                    )
                    f.write(f"{flag_args[Flags.REGISTER_FLAG][1]}\n")
                    debug_logger.debug(
                        f"Appending {flag_args[Flags.REGISTER_FLAG][0]} to {complete_file=}"
                    )
                    f.write(f"{flag_args[Flags.REGISTER_FLAG][0]}\n")
                    completer_commands.append(flag_args[Flags.REGISTER_FLAG][1])
            case Flags.PRINT_FLAG:
                command_to_search_for = flag_args[Flags.PRINT_FLAG][0]
                try:
                    path = get_path_by_completer_command(command_to_search_for)
                    print(f"complete -C '{path}' {command_to_search_for}")
                except ValueError as v:
                    debug_logger.debug("VALUE ERROR")
                    raise CompleteNotFoundException(command_to_search_for) from v
            case Flags.REMOVE_FLAG:
                command_to_remove = flag_args[flag][0]
                debug_logger.debug(f"{command_to_remove=}, {completer_commands=}")
                if command_to_remove not in completer_commands:
                    return
                remove_from_completer_command(command_to_remove)
            case _:
                print(f"{flag} is the last prev flag")

    try:
        for index, arg in enumerate(args):
            debug_logger.debug(f"{index=}, {arg=}, {prev_flag=}")
            debug_logger.debug(f"{flag_args=}")
            if prev_flag is not None:
                if (
                    arg not in FLAGS
                    and len(flag_args[prev_flag]) == max_flag_args_count[prev_flag]
                ):
                    raise InvalidArgumentException(
                        f"Too many arguments after {prev_flag}"
                    )
                if (
                    arg in FLAGS
                    and len(flag_args[prev_flag]) < min_flag_args_count[prev_flag]
                ):
                    raise InvalidArgumentException(
                        f"Not enough arguments after {prev_flag}"
                    )
                if arg in FLAGS:
                    perform_action_by_prevflag(prev_flag)
            """
            if arg == Flags.REGISTER_FLAG:
                debug_logger.debug("Arg is register flag.")
                prev_flag = Flags.REGISTER_FLAG
                flag_pos[Flags.REGISTER_FLAG] = index
                if index >= len(args) - 2:
                    raise InvalidArgumentException("Must specify command script path and command after the -C flag.")
                continue
            if arg == Flags.PRINT_FLAG:
                debug_logger.debug("Arg is print flag.")
                prev_flag = Flags.PRINT_FLAG
                flag_pos[Flags.PRINT_FLAG] = index
                if index == len(args) - 1:
                    raise CompleteNotFoundException("")
                continue
            if arg == Flags.REMOVE_FLAG:
                debug_logger.debug("Arg is remove flag.")
                prev_flag = Flags.REMOVE_FLAG
                flag_pos[arg] = index
                if index == len(args) - 1:
                    pass
            """
            if arg in FLAGS:
                debug_logger.debug(f"Arg is {arg} flag")
                prev_flag = arg
                flag_pos[arg] = index
                if index > len(args) - min_flag_args_count[flag]:
                    if arg == Flags.PRINT_FLAG:
                        raise CompleteNotFoundException("")
                    elif arg == Flags.REMOVE_FLAG:
                        pass
                    else:
                        raise InvalidArgumentException(
                            f"Must specify command scrpt path and command after the {arg} flag."
                        )
                continue
            if prev_flag in FLAGS:
                flag_args[prev_flag].append(arg)
        debug_logger.debug(f"{flag_args=}")
        if prev_flag is not None:
            if len(flag_args[prev_flag]) > max_flag_args_count[prev_flag]:
                raise InvalidArgumentException(f"Too many arguments after {prev_flag}")
            if len(flag_args[prev_flag]) < min_flag_args_count[prev_flag]:
                raise InvalidArgumentException(
                    f"Not enough arguments after {prev_flag}"
                )
            perform_action_by_prevflag(prev_flag)
    except CompleteNotFoundException as comp:
        print(f"complete: {comp.args[0]}: no completion specification", file=sys.stderr)
    except InvalidArgumentException as comp:
        print(f"complete: {comp.args[0]}")


def process_cd(args: list):
    goal_path_str = ""
    try:
        if len(args) > 1:
            raise TooManyArgumentsException("Too many arguments")
        goal_path_str = args[0]
        if goal_path_str[0] == "/":
            goal_path = pathlib.Path(goal_path_str)
            if goal_path.is_dir():
                try:
                    os.chdir(goal_path)
                except OSError as e:
                    sys.stderr.write(f"Error: {e}")
                    sys.stderr.flush()
            else:
                print(
                    f"{Commands.cd_cmd}: {goal_path_str}: No such file or directory",
                    file=sys.stderr,
                )
            return
        cwd = os.getcwd()
        goal_path_tokens = goal_path_str.split("/")
        queue = deque(goal_path_tokens)
        curr_path = pathlib.Path(cwd)
        home_path = pathlib.Path.home()
        index = -1
        while queue:
            index += 1
            current = queue.popleft()
            if index == 0 and current == "~":
                curr_path = home_path
                continue
            if current == "..":
                if str(curr_path) == "/":
                    continue
                curr_path = curr_path.parents[0]
                continue
            if current == ".":
                continue
            if current == "":
                continue
            found = False
            for f in curr_path.iterdir():
                if not f.is_dir():
                    continue
                suffix = str(f).split("/")[-1]
                if suffix == str(current):
                    curr_path = curr_path / f
                    found = True
                    break
            if found:
                continue
            raise DirectoryNotFoundException(f"{goal_path_str} is not a directory")
        os.chdir(curr_path)
    except DirectoryNotFoundException:
        print(f"cd: {goal_path_str}: No such file or directory", file=sys.stderr)
    except TooManyArgumentsException:
        print("cd: Too many arguments", file=sys.stderr)
    except OSError:
        sys.stderr.write(f"Error: {e}")
        sys.stderr.flush()


def process_echo(args: list):
    # print(f"{args=}")
    print(" ".join(args))


def process_type(args: list):
    for arg in args:
        if check_builtin(arg):
            print(f"{arg} is a shell builtin")
        else:
            path_rv = get_command_path(arg)
            if path_rv == Commands.null_cmd:
                print_not_found(arg)
            else:
                print_command_fullpath(arg, path_rv)


def run_command(command_tokens: list, stdout, stderr):
    if command_tokens == Commands.null_cmd:
        return
    command = command_tokens[0]
    args = []
    if len(command_tokens) > 1:
        args = command_tokens[1 : len(command_tokens)]
        args = [arg for arg in args if arg != ""]
    match command:
        case Commands.exit_cmd:
            return Signal.exit_signal
        case Commands.echo_cmd:
            process_echo(args)
        case Commands.type_cmd:
            process_type(args)
        case Commands.pwd_cmd:
            cwd = os.getcwd()
            print(cwd)
        case Commands.cd_cmd:
            if len(command) == 1:
                return
            process_cd(args)
        case Commands.complete_cmd:
            process_complete(args)
        case _:
            cmd_path = get_command_path(command)
            if cmd_path == Commands.null_cmd:
                print_command_not_found(command)
                return
            if len(args) == 0:
                subprocess.run(command, stdout=stdout, stderr=stderr)
                return
            subprocess.run(command_tokens, stdout=stdout, stderr=stderr)


class TokenizedMessage:
    def __init__(self, original_message):
        self.original_message = original_message
        self.stripped = original_message.strip()
        self.tokens = []
        self.single_quote_index_pairs = []
        self.double_quote_index_pairs = []
        self.backslash_indices = []
        self.redirect_index_pairs = []
        self.invalid_message = True
        self.fd_table = {}
        self.fd_mode = {}
        try:
            (
                self.single_quote_index_pairs,
                self.double_quote_index_pairs,
                self.backslash_indices,
            ) = self.preprocess_quotes(self.original_message)
            self.handle_redirections(self.stripped)
            self.command = self.get_command(self.stripped, self.redirect_index_pairs)
            debug_logger.debug(f"{self.command=}")
            self.command_tokens = self.tokenize_command(
                self.command,
                self.single_quote_index_pairs,
                self.double_quote_index_pairs,
            )
        except InvalidStringException:
            print(f"Error: Incomplete quotes detected.", file=sys.stderr)

    def get_command(self, stripped: str, redirect_index_pairs: list[tuple]):
        command = stripped
        if len(redirect_index_pairs) == 0:
            return command
        command = stripped[0 : redirect_index_pairs[0][0]]
        return command

    def handle_redirections(self, stripped: str):
        if stripped == "":
            return
        if stripped[-1] == ">":
            raise UnexpectedTokenException("Must redirect to a file with a name")
        stripped = stripped.strip()
        further_inspect = []
        single_quote_index = 0
        double_quote_index = 0
        backslash_index = 0
        prev_character_redirect = False
        prev_character_double_redirect = False
        for index, character in enumerate(stripped):
            single_quote_left = -1
            single_quote_right = -1
            double_quote_left = -1
            double_quote_right = -1
            backslash = -1
            if len(self.backslash_indices) > backslash_index:
                backslash = self.backslash_indices[backslash_index]
            if len(self.single_quote_index_pairs) > single_quote_index:
                single_quote_left = self.single_quote_index_pairs[single_quote_index][0]
                single_quote_right = self.single_quote_index_pairs[single_quote_index][
                    1
                ]
            if len(self.double_quote_index_pairs) > double_quote_index:
                double_quote_left = self.double_quote_index_pairs[double_quote_index][0]
                double_quote_right = self.double_quote_index_pairs[double_quote_index][
                    1
                ]
            if index == backslash + 1 and backslash != -1:
                backslash_index += 1
                prev_character_redirect = False
                continue
            if double_quote_left <= index < double_quote_right:
                prev_character_redirect = False
                continue
            if index == double_quote_right:
                double_quote_index += 1
                prev_character_redirect = False
                continue
            if single_quote_left <= index < single_quote_right:
                prev_character_redirect = False
                continue
            if index == single_quote_right:
                prev_character_redirect = False
                single_quote_index += 1
                continue
            if character == ">":
                if prev_character_double_redirect:
                    raise UnexpectedTokenException(
                        "Invalid Redirect syntax: must have >> or > or << or < or |"
                    )
                if prev_character_redirect:
                    prev_character_double_redirect = True
                    further_inspect.pop()
                    further_inspect.append(index)
                    continue
                prev_character_redirect = True
                further_inspect.append(index)
                continue
            prev_character_redirect = False
            debug_logger.debug(f"{further_inspect=}")
        # format: command1 > file > file > ....
        redirect_indices = []
        redirect_fds = []
        debug_logger.debug(f"{stripped=}")
        for index in further_inspect:
            j = index - 1
            token = ">"
            original_token = token
            fd = ""
            while j >= 0:
                if stripped[j] == " ":
                    break
                if not stripped[j].isdigit() and not stripped[j] == ">":
                    j = index - 1
                    token = original_token
                    fd = "1"
                    break
                if stripped[j] != ">":
                    fd = stripped[j] + fd
                token = stripped[j] + token
                j -= 1
            if fd == "":
                fd = "1"
            self.fd_mode[int(fd)] = WRITE_FLAG
            if ">>" in token:
                self.fd_mode[int(fd)] = APPEND_FLAG

            debug_logger.debug(f"{token=}")
            redirect_indices.append((j + 1, index))  # redirect_index[i] = left, right
            redirect_fds.append(fd)
        debug_logger.debug(f"{redirect_indices=} {len(redirect_indices)=}")
        debug_logger.debug(f"{redirect_fds=}")
        for i in range(len(redirect_indices)):
            R = redirect_indices[i][1]
            next_L = len(stripped)
            if i + 1 >= len(redirect_indices):
                next_L = len(stripped)
            else:
                next_L = redirect_indices[i + 1][0]
            fd = redirect_fds[i]
            files = stripped[R + 1 : next_L].strip()
            debug_logger.debug(f"{files=}")
            splitted = files.split()
            self.fd_table[int(fd)] = []
            for file in splitted:
                if file == "":
                    continue
                self.fd_table[int(fd)].append(file)

        self.redirect_index_pairs = redirect_indices
        debug_logger.debug(f"{self.fd_table=}")

    def run_tokenized_command(self) -> Signal:
        files_stdout = []
        files_stderr = []
        stdout_flag = WRITE_FLAG
        stderr_flag = WRITE_FLAG
        if STDOUT_FD in self.fd_table:
            files_stdout = self.fd_table[STDOUT_FD]
            if self.fd_mode[STDOUT_FD] == APPEND_FLAG:
                stdout_flag = APPEND_FLAG
        if STDERR_FD in self.fd_table:
            files_stderr = self.fd_table[STDERR_FD]
            if self.fd_mode[STDERR_FD] == APPEND_FLAG:
                stderr_flag = APPEND_FLAG

        rv = None
        if len(files_stdout) == 0 and len(files_stderr) == 0:
            rv = run_command(self.command_tokens, sys.stdout, sys.stderr)
        elif len(files_stdout) > 0 and len(files_stderr) == 0:
            reference_file = files_stdout[0]
            with open(reference_file, stdout_flag) as desired_stdout:
                with redirect_stdout(desired_stdout):
                    rv = run_command(self.command_tokens, desired_stdout, sys.stderr)
        elif len(files_stdout) == 0 and len(files_stderr) > 0:
            reference_file = files_stderr[0]
            with open(reference_file, stderr_flag) as desired_stderr:
                with redirect_stderr(desired_stderr):
                    rv = run_command(self.command_tokens, sys.stdout, desired_stderr)
        else:
            reference_file = files_stdout[0]
            reference_file_err = files_stderr[0]
            with (
                open(reference_file, stdout_flag) as desired_stdout,
                open(reference_file_err, stderr_flag) as desired_stderr,
            ):
                with redirect_stdout(desired_stdout), redirect_stderr(desired_stderr):
                    rv = run_command(
                        self.command_tokens, desired_stdout, desired_stderr
                    )
        return rv

    def preprocess_quotes(self, stripped: str):
        if stripped == "":
            return Commands.null_cmd
        double_quote_escapable_characters = ['"', "\\", "$", "`", "\n"]
        single_quoted_tokens = []  # [str_enclosed_in_singlequotes1, str_enclosed_in_singlequotes2]
        single_quote_index_pairs = []  # [(i1_1, i1_2), (i2_1, i2_2), .... (in_1, in_2)]

        single_quote_one_found = False
        last_single_quote_index = -1
        double_quoted_tokens = []
        double_quote_index_pairs = []
        double_quote_one_found = False
        last_double_quote_index = -1
        prev_character_backslash = False
        backslash_indices = []
        special_characters = {'"', "'", "\\"}
        for index, character in enumerate(stripped):
            debug_logger.debug(f"{single_quoted_tokens=}")
            debug_logger.debug(f"{single_quote_index_pairs=}")
            debug_logger.debug(f"{single_quote_one_found=}")
            debug_logger.debug(f"{double_quoted_tokens=}")
            debug_logger.debug(f"{double_quote_index_pairs=}")
            debug_logger.debug(f"{double_quote_one_found=}")
            debug_logger.debug(f"{last_single_quote_index=}")
            debug_logger.debug(f"{last_double_quote_index=}")
            debug_logger.debug(f"{prev_character_backslash=}")
            debug_logger.debug(f"{index=}, {character=}")
            debug_logger.debug(f"{backslash_indices=}")
            if (
                character == "'"
                and not double_quote_one_found
                and not prev_character_backslash
            ):
                if single_quote_one_found:
                    single_quote_index_pairs.append((last_single_quote_index, index))
                    single_quoted_tokens.append(
                        stripped[last_single_quote_index : index + 1]
                    )
                    single_quote_one_found = False
                else:
                    last_single_quote_index = index
                    single_quote_one_found = True
                continue
            if (
                character == "\\"
                and not single_quote_one_found
                and not prev_character_backslash
            ):
                prev_character_backslash = True
                backslash_indices.append(index)
                continue
            if (
                character == '"'
                and not single_quote_one_found
                and not prev_character_backslash
            ):
                if double_quote_one_found:
                    double_quote_index_pairs.append((last_double_quote_index, index))
                    double_quoted_tokens.append(
                        stripped[last_double_quote_index : index + 1]
                    )
                    double_quote_one_found = False
                else:
                    last_double_quote_index = index
                    double_quote_one_found = True
                continue
            prev_character_backslash = False
        if single_quote_one_found:
            raise InvalidStringException("Invalid Quote Scheme")
        if double_quote_one_found:
            raise InvalidStringException("Invalid Quote Scheme")
        return single_quote_index_pairs, double_quote_index_pairs, backslash_indices

    # returns tokens of a command i.e. [echo, arg1, arg2, ... argn]
    def tokenize_command(
        self,
        stripped: str,
        single_quote_index_pairs: list,
        double_quote_index_pairs: list,
    ):
        # assumes stripped spaces i.e. 'command arg1 arg2 ...... argn'
        # with no space to left or right
        stripped = stripped.strip()
        single_quoted_tokens = []
        double_quoted_tokens = []
        for a, b in single_quote_index_pairs:
            single_quoted_tokens.append(stripped[a + 1 : b])
        for a, b in double_quote_index_pairs:
            double_quoted_tokens.append(stripped[a + 1 : b])
        debug_logger.debug("### Single quote tokens ###")
        for index, token in enumerate(single_quoted_tokens):
            debug_logger.debug(f"token {index}:")
            debug_logger.debug(token)
            debug_logger.debug(f"index: {single_quote_index_pairs[index]}")
        debug_logger.debug("### Single quote tokens finished ###")
        debug_logger.debug("### Double quote tokens finished ###")
        for index, token in enumerate(double_quoted_tokens):
            debug_logger.debug(f"token {index}:")
            debug_logger.debug(token)
            debug_logger.debug(f"index: {double_quote_index_pairs[index]}")
        debug_logger.debug("### Double quote tokens finished ###")
        last_char = ""
        curr_token = ""
        tokens = [curr_token]
        curr_token_index = 0
        curr_single_quote_index = 0
        curr_double_quote_index = 0
        unindexed_character = "no_index"
        prev_character_backslash = False
        for index, character in enumerate(stripped):
            # single quote processing
            left_single_quote_index = unindexed_character
            right_single_quote_index = unindexed_character
            if curr_single_quote_index < len(single_quote_index_pairs):
                left_single_quote_index = single_quote_index_pairs[
                    curr_single_quote_index
                ][0]
                right_single_quote_index = single_quote_index_pairs[
                    curr_single_quote_index
                ][1]
            if (
                left_single_quote_index != unindexed_character
                and left_single_quote_index <= index < right_single_quote_index
            ):
                if character != "'":
                    tokens[curr_token_index] += character
                continue
            if index == right_single_quote_index:
                curr_single_quote_index += 1
                continue
            # single quote processing done
            if character == "\\" and not prev_character_backslash:
                prev_character_backslash = True
                continue
            if prev_character_backslash:
                tokens[curr_token_index] += character
                prev_character_backslash = False
                continue
            # double quote processing
            left_double_quote_index = unindexed_character
            right_double_quote_index = unindexed_character
            if curr_double_quote_index < len(double_quote_index_pairs):
                left_double_quote_index = double_quote_index_pairs[
                    curr_double_quote_index
                ][0]
                right_double_quote_index = double_quote_index_pairs[
                    curr_double_quote_index
                ][1]
            if (
                left_double_quote_index != unindexed_character
                and left_double_quote_index <= index < right_double_quote_index
            ):
                if character != '"':
                    tokens[curr_token_index] += character
                continue
            if index == right_double_quote_index:
                curr_double_quote_index += 1
                continue
            # double quote processing done
            # escaped
            if character == " " and last_char == " ":
                continue
            if character == " ":
                curr_token_index += 1
                tokens.append("")
                continue
            tokens[curr_token_index] += character
        debug_logger.debug("Tokenized message: ")
        for token in tokens:
            debug_logger.debug(token)
        return tokens


# input: message
# output: tokens
def process_command(msg: str):
    msg = msg.strip()
    if msg == "":
        return
    tokenized_message = TokenizedMessage(msg)
    signal = tokenized_message.run_tokenized_command()
    return signal


executables = get_all_system_commands()
completer_commands = get_all_completer_commands()


# gnu readline completer function for tab completion on commands
def complete(text, state):
    options = []
    start = readline.get_begidx()
    line_buffer = readline.get_line_buffer()
    # print(f"{start=} {text=}, {state=}, {line_buffer=}")
    left_stripped_line_buffer = line_buffer.lstrip()
    space_splitted_line_buffer = left_stripped_line_buffer.split(" ")
    first_line_buffer_token = space_splitted_line_buffer[0]
    if start == len(line_buffer) - len(left_stripped_line_buffer):
        options = Commands.available_commands + list(
            set(executables) - set(Commands.available_commands)
        )
        options = options + list(set(completer_commands) - set(options))
        options = [f"{option} " for option in options if option.startswith(text)]
    elif first_line_buffer_token in completer_commands:
        path = get_path_by_completer_command(first_line_buffer_token)
        argv = ["", "", "", ""]
        argv[0] = path
        argv[1] = first_line_buffer_token
        argv[2] = text
        argv[3] = ""
        if len(space_splitted_line_buffer) >= 2:
            argv[3] = space_splitted_line_buffer[len(space_splitted_line_buffer) - 2]
        COMP_LINE = "COMP_LINE"
        COMP_POINT = "COMP_POINT"
        os.environ[COMP_LINE] = line_buffer
        os.environ[COMP_POINT] = f"{len(line_buffer)}"
        result = subprocess.run(argv, stdout=subprocess.PIPE)
        decoded = result.stdout.decode("UTF-8")
        decoded = decoded[: len(decoded) - 1]
        options = decoded.split("\n")
        options = [f"{option} " for option in options if option.startswith(text)]
    else:
        p = pathlib.Path(os.getcwd())
        split = text.split("/")
        curr_path = p
        for token in split[:-1]:
            curr_path = curr_path / token
        prefix = "/".join(split[:-1])
        if curr_path.is_dir():
            for path in curr_path.iterdir():
                name = str(path).split("/")[-1]
                if not name.startswith(split[-1]):
                    continue
                if path.is_dir():
                    if prefix != "":
                        options.append(f"{prefix}/{name}/")
                    else:
                        options.append(f"{name}/")
                else:
                    if prefix != "":
                        options.append(f"{prefix}/{name} ")
                    else:
                        options.append(f"{name} ")
    try:
        return options[state]
    except IndexError:
        return None


def main():
    debug_logger.debug("Started")
    # line for tab completion
    readline.parse_and_bind("tab: complete")
    readline.set_completer(complete)
    readline.set_completer_delims(" ")
    while True:
        msg = input("$ ")
        signal = process_command(msg)
        if signal == Signal.exit_signal:
            return


if __name__ == "__main__":
    with open(complete_file, WRITE_FLAG) as f:
        pass
    main()