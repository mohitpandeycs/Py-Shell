<h1 align="center">Py-Shell</h1>
<p align="center">
  A Unix-style shell built from scratch in Python — no wrapping, no shortcuts.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Dependencies-None-informational?style=flat-square" />
  <img src="https://img.shields.io/badge/Platform-Unix--like-lightgrey?style=flat-square&logo=linux&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-blue?style=flat-square" />
</p>

---

## What is Py-Shell?

Py-Shell is a minimal command-line shell written entirely in Python, built to answer one question: what actually happens between typing a command and seeing output on screen? It parses input, resolves built-ins vs. executables, handles quoting and redirection, and runs background jobs — all without leaning on an existing shell implementation. It's not trying to replace Bash. It's trying to explain it.

---

## Features

- **Interactive REPL** — Reads, parses, and executes commands in a live loop, just like a real shell.
- **Built-in Commands** — `cd`, `pwd`, `echo`, `type`, `history`, `complete`, `jobs`, `exit` — implemented, not imported.
- **Executable Discovery** — Walks `PATH` to resolve external commands, cross-platform via `pathlib`.
- **Full Redirection Support** — `>`, `>>`, `2>`, `2>>`, and explicit `1>` / `1>>` forms for stdout/stderr.
- **Quoting & Escaping** — A dedicated parser handles single quotes, double quotes, and escaped characters correctly.
- **Tab Completion** — Integrates Python's `readline` with a custom completer built on the executable discovery logic.
- **Command History** — Every command entered in a session is tracked and inspectable via `history`.
- **Background Jobs** — Run commands with `&` and track them through a lightweight job-handling system.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Core Shell | Python 3.14 |
| Process Execution | `subprocess` |
| Path Handling | `pathlib` |
| Completion & Input | `readline` |
| Dependencies | None — standard library only |

---

## Architecture

```text
Py-Shell/
│
├── app/
│   ├── main.py       # REPL, parsing, redirection, completion
│   └── builtin.py    # cd, pwd, echo, type, history, complete, jobs
│
├── pyproject.toml
├── uv.lock
├── .python-version
└── your_program.sh
```

**`app/main.py`** drives the shell — reading input, parsing it, routing to built-ins or external processes, and handling redirection and errors along the way.

**`app/builtin.py`** holds every built-in command plus the executable discovery and shell-state logic that powers them.

---

## How It Works

```text
User Input
    │
    ▼
Command Line Parser
    │
    ├── Built-in ──► Built-in Handler
    │
    └── External ──► Executable Discovery ──► Process Execution ──► stdout / stderr
```

Quoted and escaped input goes through a dedicated parser to keep argument structure intact. Redirection operators (`>`, `>>`, `2>`, `2>>`) are split off from the command before execution, and output is routed to the right file.

---

## Getting Started

Clone it:

```bash
git clone https://github.com/mohitpandeycs/Py-Shell.git
cd Py-Shell
```

Run it:

```bash
python app/main.py
```

Or, with [uv](https://docs.astral.sh/uv/):

```bash
uv run python app/main.py
```

You'll land on the prompt:

```text
$
```

---

## Example Session

```text
$ pwd
/home/user/Py-Shell

$ echo "Hello, World!"
Hello, World!

$ type echo
echo is a shell builtin

$ echo "Py-Shell" > output.txt

$ cat output.txt
Py-Shell

$ sleep 5 &

$ jobs

$ exit
```

---

## Requirements

- Python **3.14+**
- A Unix-like environment (for the full shell experience)
- Zero third-party dependencies

---

## Limitations

Py-Shell is a learning project, not a Bash replacement. Not (yet) implemented:

- Pipelines (`|`)
- Environment-variable expansion
- Wildcard/glob expansion
- Command substitution
- Full POSIX grammar
- Complex job control

---

## Roadmap

- [ ] Pipeline support
- [ ] Environment-variable expansion
- [ ] Glob/wildcard expansion
- [ ] Improved job control
- [ ] Persistent command history
- [ ] Full POSIX-style parsing
- [ ] Automated test coverage
- [ ] Custom prompt configuration

---

## Contributing

1. Fork the repo
2. `git checkout -b feature/your-feature`
3. Make your changes, test them
4. `git commit -m "Add your feature"`
5. `git push origin feature/your-feature`
6. Open a PR

For bigger changes, open an issue first so we can talk through the approach.

---
## Connect With Me :)

Built and maintained by **[Mohit Pandey](https://github.com/mohitpandeycs)**

- GitHub — [@mohitpandeycs](https://github.com/mohitpandeycs)
- LinkedIn — [in/mohitpandeycs](https://linkedin.com/in/mohitpandeycs)

---

## License

This project is released under [MIT License](https://opensource.org/licenses/MIT).

>  If you find this useful, consider giving it a ⭐ Star — it helps other developers discover the project.

<p align="center">
  <sub>Built by <a href="https://github.com/mohitpandeycs">Mohit Pandey</a> — a hands-on look at how shells actually work.</sub>
</p>
