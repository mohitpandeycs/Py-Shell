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
            pipe_idx = command_parts.index("|")
            cmd1_parts = command_parts[:pipe_idx]
            cmd2_parts = command_parts[pipe_idx + 1 :]

            if not cmd1_parts or not cmd2_parts:
                continue

            path1 = shutil.which(cmd1_parts[0])
            path2 = shutil.which(cmd2_parts[0])

            if path1 and path2:
                p1 = subprocess.Popen(cmd1_parts, stdout=subprocess.PIPE)
                p2 = subprocess.Popen(cmd2_parts, stdin=p1.stdout)
                p1.stdout.close()
                p2.communicate()
            else:
                if not path1:
                    print(f"{cmd1_parts[0]}: not found")
                if not path2:
                    print(f"{cmd2_parts[0]}: not found")
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