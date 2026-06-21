import sys
import os
import shutil
import subprocess
import shlex


def main():
    jobs_list = []

    while True:
        for job in jobs_list:
            if job["status"] == "Running":
                poll_result = job["process"].poll()
                if poll_result is not None:
                    job["status"] = "Done"

        jobs_list.sort(key=lambda x: x["id"])
        jobs_to_remove = []

        for job in jobs_list:
            if job["status"] == "Done":
                marker = " "
                if job == jobs_list[-1]:
                    marker = "+"
                elif len(jobs_list) > 1 and job == jobs_list[-2]:
                    marker = "-"

                status_str = "Done".ljust(21)
                print(f"[{job['id']}]{marker}  {status_str}{job['command']}")
                jobs_to_remove.append(job)

        for job in jobs_to_remove:
            jobs_list.remove(job)

        sys.stdout.write("$ ")
        sys.stdout.flush()
        command = input()

        if not command.strip():
            continue

        try:
            command_parts = shlex.split(command)
        except ValueError:
            continue

        is_background = False
        if command_parts and command_parts[-1] == "&":
            is_background = True
            command_parts.pop()
        elif command_parts and command_parts[-1].endswith("&"):
            is_background = True
            command_parts[-1] = command_parts[-1][:-1]

        if "|" in command_parts:
            pipeline_cmds = []
            current_cmd = []
            for part in command_parts:
                if part == "|":
                    if current_cmd:
                        pipeline_cmds.append(current_cmd)
                        current_cmd = []
                else:
                    current_cmd.append(part)
            if current_cmd:
                pipeline_cmds.append(current_cmd)

            if not pipeline_cmds:
                continue

            processes = []
            prev_stdout = None

            for i, cmd in enumerate(pipeline_cmds):
                is_last = i == len(pipeline_cmds) - 1
                stdout_target = sys.stdout if is_last else subprocess.PIPE

                prog = cmd[0]
                args = cmd[1:]

                if prog == "echo":
                    output = " ".join(args) + "\n"
                    p = subprocess.Popen(
                        ["echo", output.strip()],
                        stdin=prev_stdout,
                        stdout=stdout_target,
                        text=True,
                    )
                elif prog == "pwd":
                    output = os.getcwd() + "\n"
                    p = subprocess.Popen(
                        ["echo", output.strip()],
                        stdin=prev_stdout,
                        stdout=stdout_target,
                        text=True,
                    )
                elif prog == "type":
                    if args:
                        target = args[0]
                        if target in ["echo", "exit", "type", "pwd", "cd", "jobs"]:
                            output = f"{target} is a shell builtin"
                        else:
                            path = shutil.which(target)
                            if path:
                                output = f"{target} is {path}"
                            else:
                                output = f"{target}: not found"
                    else:
                        output = ""
                    p = subprocess.Popen(
                        ["echo", output],
                        stdin=prev_stdout,
                        stdout=stdout_target,
                        text=True,
                    )
                else:
                    path = shutil.which(prog)
                    if path:
                        p = subprocess.Popen(
                            cmd, stdin=prev_stdout, stdout=stdout_target
                        )
                    else:
                        print(f"{prog}: not found")
                        break

                if prev_stdout:
                    prev_stdout.close()

                prev_stdout = p.stdout
                processes.append(p)

            if processes:
                processes[-1].communicate()
            continue

        stdout_file = None
        stderr_file = None
        append_stdout = False
        append_stderr = False

        if "2>>" in command_parts:
            idx = command_parts.index("2>>")
            stderr_file = command_parts[idx + 1]
            command_parts = command_parts[:idx]
            append_stderr = True

        elif ">>" in command_parts or "1>>" in command_parts:
            operator = ">>" if ">>" in command_parts else "1>>"
            idx = command_parts.index(operator)
            stdout_file = command_parts[idx + 1]
            command_parts = command_parts[:idx]
            append_stdout = True

        elif "2>" in command_parts:
            idx = command_parts.index("2>")
            stderr_file = command_parts[idx + 1]
            command_parts = command_parts[:idx]

        elif ">" in command_parts or "1>" in command_parts:
            operator = ">" if ">" in command_parts else "1>"
            idx = command_parts.index(operator)
            stdout_file = command_parts[idx + 1]
            command_parts = command_parts[:idx]

        if not command_parts:
            continue

        program_name = command_parts[0]
        args = command_parts[1:]

        if program_name == "exit":
            break

        if program_name == "jobs":
            target_job_id = None
            if args:
                try:
                    target_job_id = int(args[0])
                except ValueError:
                    pass

            jobs_list.sort(key=lambda x: x["id"])
            jobs_to_remove = []

            for job in jobs_list:
                if target_job_id is not None and job["id"] != target_job_id:
                    continue

                if job["status"] == "Running":
                    if job["process"].poll() is not None:
                        job["status"] = "Done"

                marker = " "
                if job == jobs_list[-1]:
                    marker = "+"
                elif len(jobs_list) > 1 and job == jobs_list[-2]:
                    marker = "-"

                status_str = job["status"].ljust(21)
                if job["status"] == "Done":
                    print(f"[{job['id']}]{marker}  {status_str}{job['command']}")
                    jobs_to_remove.append(job)
                else:
                    print(f"[{job['id']}]{marker}  {status_str}{job['command']} &")

            for job in jobs_to_remove:
                jobs_list.remove(job)
            continue

        if program_name == "echo":
            output = " ".join(args)
            if stdout_file:
                mode = "a" if append_stdout else "w"
                with open(stdout_file, mode) as f:
                    f.write(output + "\n")
            else:
                print(output)
            if stderr_file:
                open(stderr_file, "w").close()
            continue

        if program_name == "pwd":
            output = os.getcwd()
            if stdout_file:
                mode = "a" if append_stdout else "w"
                with open(stdout_file, mode) as f:
                    f.write(output + "\n")
            else:
                print(output)
            continue

        if program_name == "cd":
            if not args:
                continue
            target = args[0]
            if target == "~":
                target = os.environ.get("HOME")
            try:
                os.chdir(target)
            except FileNotFoundError:
                print(f"cd: {target}: No such file or directory")
            continue

        if program_name == "type":
            if not args:
                continue
            target = args[0]
            if target in ["echo", "exit", "type", "pwd", "cd", "jobs"]:
                print(f"{target} is a shell builtin")
            else:
                path = shutil.which(target)
                if path:
                    print(f"{target} is {path}")
                else:
                    print(f"{target}: not found")
            continue

        path = shutil.which(program_name)

        if path:
            f_out = (
                open(stdout_file, "a" if append_stdout else "w")
                if stdout_file
                else None
            )
            f_err = (
                open(stderr_file, "a" if append_stderr else "w")
                if stderr_file
                else None
            )

            try:
                if is_background:
                    p = subprocess.Popen(
                        [program_name] + args, stdout=f_out, stderr=f_err
                    )

                    existing_ids = {j["id"] for j in jobs_list}
                    next_id = 1
                    while next_id in existing_ids:
                        next_id += 1

                    raw_cmd = f"{program_name} " + " ".join(args)
                    print(f"[{next_id}] {p.pid}")

                    jobs_list.append(
                        {
                            "id": next_id,
                            "process": p,
                            "command": raw_cmd.strip(),
                            "status": "Running",
                            "printed_done": False,
                        }
                    )
                else:
                    subprocess.run([program_name] + args, stdout=f_out, stderr=f_err)
            finally:
                if not is_background:
                    if f_out:
                        f_out.close()
                    if f_err:
                        f_err.close()
        else:
            print(f"{command}: not found")


if __name__ == "__main__":
    main()